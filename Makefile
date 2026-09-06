DATASTORES ?= docker compose -f docker-compose.datastores.yml
ASTERISK   ?= docker compose -f docker-compose.asterisk.yml
COMPOSE    ?= docker compose
UV         ?= uv
NPM        ?= npm
APP_DIR    ?= pana-app
LANDING_DIR ?= pana-landing

CELERY := $(UV) run celery -A celery_service.celery_app worker --loglevel=info

ifeq ($(OS),Windows_NT)
CELERY_POOL ?= solo
else
CELERY_POOL ?= prefork
endif

.DEFAULT_GOAL := help
.PHONY: asterisk-call asterisk-watch asterisk-build asterisk-up asterisk-down asterisk-logs asterisk-cli asterisk-check asterisk-secret help install install-frontend install-landing up down logs backend frontend frontend-build lint-frontend lint-frontend-fix landing landing-build lint-landing lint-landing-fix celery celery-high celery-default lint format check test alembic-up alembic-create deploy-build deploy-up deploy-down

install:
	$(UV) sync --group dev

install-frontend:
	$(NPM) --prefix $(APP_DIR) install

install-landing:
	$(NPM) --prefix $(LANDING_DIR) install

# --- Development datastores -------------------------------------------------

up:
	$(DATASTORES) up -d

down:
	$(DATASTORES) down

# --- Application processes (run on the host) --------------------------------

backend:
	$(UV) run python backend.py

frontend:
	$(NPM) --prefix $(APP_DIR) run dev

frontend-build:
	$(NPM) --prefix $(APP_DIR) run build

landing:
	$(NPM) --prefix $(LANDING_DIR) run dev

landing-build:
	$(NPM) --prefix $(LANDING_DIR) run build

celery:
	$(CELERY) -P $(CELERY_POOL) -Q high_priority,default -n worker@%h

celery-high:
	$(CELERY) -P $(CELERY_POOL) -Q high_priority -n high_worker@%h

celery-default:
	$(CELERY) -P $(CELERY_POOL) -Q default -n default_worker@%h

# --- Telephony (Asterisk SIP trunk) -----------------------------------------
# Credentials live in secrets/sip_trunk.env, which is git-ignored and mounted
# into the container read-only. See docs/telephony.md.

asterisk-secret:
	@if [ -f secrets/sip_trunk.env ]; then \
		echo "secrets/sip_trunk.env already exists, leaving it alone"; \
	else \
		cp secrets/sip_trunk.env.example secrets/sip_trunk.env; \
		chmod 600 secrets/sip_trunk.env; \
		echo "created secrets/sip_trunk.env (mode 600) -- fill in the carrier values"; \
	fi

asterisk-build:
	$(ASTERISK) build

asterisk-up:
	@test -f secrets/sip_trunk.env || { echo "secrets/sip_trunk.env is missing; run: make asterisk-secret"; exit 1; }
	$(ASTERISK) up -d

asterisk-down:
	$(ASTERISK) down

asterisk-logs:
	$(ASTERISK) logs -f

asterisk-cli:
	docker exec -it asterisk-pana asterisk -rvvv

asterisk-check:
	./asterisk/bin/smoke-test.sh

# Place a test call out through the carrier: make asterisk-call NUMBER=...
asterisk-call:
ifndef NUMBER
	$(error NUMBER is required, e.g. make asterisk-call NUMBER=9779812345678)
endif
	./asterisk/bin/test-call.sh $(NUMBER)

# Watch inbound calls arrive. Ring your DID while this runs.
asterisk-watch:
	docker exec asterisk-pana asterisk -rx 'pjsip set logger on'
	@echo "Tracing. Ring your DID now. Ctrl-C to stop."
	@docker logs -f --since 1s asterisk-pana 2>&1 | grep -viE "declined to load|Unable to load config file" || true

# --- Code quality -----------------------------------------------------------

lint:
	$(UV) run ruff check --fix .

format:
	$(UV) run ruff format .

lint-frontend:
	$(NPM) --prefix $(APP_DIR) run lint

lint-frontend-fix:
	$(NPM) --prefix $(APP_DIR) run lint:fix

lint-landing:
	$(NPM) --prefix $(LANDING_DIR) run lint

lint-landing-fix:
	$(NPM) --prefix $(LANDING_DIR) run lint:fix

test:
	$(UV) run pytest

check:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

# --- Migrations -------------------------------------------------------------

alembic-up:
	$(UV) run alembic upgrade head

alembic-create:
ifndef MSG
	$(error MSG is required, e.g. make alembic-create MSG="add users table")
endif
	$(UV) run alembic revision -m "$(MSG)"

# --- Deployment stack (datastores + pana-image) -----------------------------

deploy-build:
	$(COMPOSE) build

deploy-up:
	$(COMPOSE) up -d

deploy-down:
	$(COMPOSE) down

# --- Make Help -----------------------------
help:
	@echo "make install         sync the Python environment with uv"
	@echo "make install-frontend  install the app dependencies"
	@echo "make install-landing   install the landing page dependencies"
	@echo "make up              start Postgres and Redis for development"
	@echo "make down            stop the development datastores"
	@echo "make logs            tail the datastore logs"
	@echo "make backend         run the FastAPI server"
	@echo "make frontend        run the app dev server (5173)"
	@echo "make frontend-build  build the app for production"
	@echo "make landing         run the landing page dev server (5174)"
	@echo "make landing-build   build the landing page for production"
	@echo "make celery          run one worker consuming both queues"
	@echo "make celery-high     run the high priority worker only"
	@echo "make celery-default  run the default priority worker only"
	@echo "make lint            check code with ruff"
	@echo "make format          format code with ruff"
	@echo "make lint-frontend   check the app with eslint"
	@echo "make lint-landing    check the landing page with eslint"
	@echo "make test            run the test suite"
	@echo "make check           lint and format check, no writes (CI)"
	@echo "make alembic-up      apply migrations up to head"
	@echo "make alembic-create MSG=\"...\"  create an empty revision"
	@echo "make asterisk-secret create secrets/sip_trunk.env from the example"
	@echo "make asterisk-build  build the Asterisk image"
	@echo "make asterisk-up     start the SIP trunk"
	@echo "make asterisk-down   stop the SIP trunk"
	@echo "make asterisk-logs   tail the Asterisk logs"
	@echo "make asterisk-cli    open the Asterisk CLI"
	@echo "make asterisk-check  verify the trunk registered with the carrier"
	@echo "make asterisk-call NUMBER=...  place a test call out through the carrier"
	@echo "make asterisk-watch  trace inbound calls as they arrive"
	@echo "make deploy-build    build the deployment images"
	@echo "make deploy-up       start the full deployment stack"
	@echo "make deploy-down     stop the full deployment stack"
