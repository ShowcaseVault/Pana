from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException

from api.cruds.authentication import get_google_callback, get_google_login
from api.schemas.return_response import SuccessResponse, FailureResponse

router = APIRouter()

@router.get("/auth/google")
def google_login():
    try:
        url = get_google_login()
        return RedirectResponse(url)
    except HTTPException as e:
        return FailureResponse(message=str(e.detail) )
    except Exception as e:
        return FailureResponse(message="Google Signin Failed -1")

@router.get("/auth/google/callback")
def google_callback(code: str):
    try:
        user_info = get_google_callback(code)

        return SuccessResponse(data=user_info, message="Google Signin Success")
    except HTTPException as e:
        return FailureResponse(message= str(e.detail) )
    except Exception as e:
        return FailureResponse(message="Google Signin Failed -2")