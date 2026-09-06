import React from 'react';
import HeroWave from './components/HeroWave';
import './styles/page.css';

/** Where the "Start talking" buttons go. */
const APP_URL = import.meta.env.VITE_APP_URL || 'http://localhost:5173';

/**
 * The moments of the story, hung off the thread in order.
 *
 * The page is a day: each beat carries a clock time, and reading down the page
 * is reading down a day's recordings. That is the shape of the product, so it
 * is the shape of the page.
 */
const BEATS = [
  {
    time: '11:47 pm',
    heading: 'The notebook has three entries.',
    body: [
      'January the fourth, the fifth, and then a gap where the rest of the year should be. You did not lose interest in your own life. You just kept meeting the same blank page at the end of a day that had already taken everything you had.',
    ],
  },
  {
    time: '11:48 pm',
    heading: 'Writing is the wrong tool for a tired person.',
    body: [
      'It asks you to compose. To choose an opening sentence, decide what mattered, and put it in order. Those are the three hardest things to do at midnight, and all of them come before a single word is down.',
      'So the day goes unrecorded. Not because it was empty, but because the toll to enter it was too high.',
    ],
  },
];

/** The second half of the argument: what changes when you talk instead. */
const AFTER = [
  {
    time: '11:52 pm',
    heading: 'You already know how to do this.',
    body: [
      'You describe your day constantly. To a partner, on a walk, on the phone to someone who asks how it went. Nobody rehearses that. It comes out crooked and doubles back and lands anyway.',
      'Pana takes that, exactly as it comes. Say it badly. Trail off. Start again halfway through. It was built for the way people actually talk.',
    ],
  },
  {
    time: '7:30 am',
    heading: 'The next morning, it is written.',
    body: [
      'Pana transcribes what you said and writes the day up: what happened, how it went, and anything you said you needed to do. Your words, in order, made into something you can read.',
    ],
  },
];

/** The generated entry shown as proof, in the same shape the app renders it. */
const ENTRY = {
  date: 'Tuesday, 4 March',
  mood: 'unsettled, then better',
  text: 'The review went better than I had braced for. I had spent most of the morning building a version of it in my head that never happened. Afterwards I walked home the long way, past the water, and stayed out longer than I needed to. The first unhurried half hour in about a week.',
  actions: ['Send Priya the revised figures', 'Book the dentist, properly this time'],
};

const App = () => (
  <div className="page">
    <header className="masthead">
      <a className="masthead__brand" href="/">
        <img
          className="masthead__logo"
          src="/logo-app.png"
          alt=""
          width="48"
          height="48"
        />
        <span className="masthead__name">Pana</span>
      </a>
      <a className="masthead__enter" href={APP_URL}>
        Open Pana
      </a>
    </header>

    {/* --- Hero -------------------------------------------------------------
        The product running, not a description of it: the wave moves and the
        words arrive under it the way a transcript actually lands. */}
    <section className="hero">
      <h1 className="hero__line">
        A diary
        <br />
        you talk to.
      </h1>

      <HeroWave />

      <p className="hero__sub">
        Say what happened, for as long as you like. Pana listens, writes it down, and turns the
        day into something you can read.
      </p>

      <a className="button button--primary" href={APP_URL}>
        Start talking
      </a>
    </section>

    {/* --- The thread -------------------------------------------------------
        One hairline down the page with the story hung off it, timestamped.
        Reading down the page is reading down a day. */}
    <main className="thread">
      {BEATS.map((beat) => (
        <article className="beat" key={beat.time}>
          <p className="beat__time figure">{beat.time}</p>
          <div className="beat__body">
            <h2 className="beat__heading">{beat.heading}</h2>
            {beat.body.map((line) => (
              <p className="beat__text" key={line.slice(0, 24)}>
                {line}
              </p>
            ))}
          </div>
        </article>
      ))}

      {/* The turn. Marked on the thread by a filled node -- the only one, and
          the only teal in the body of the page, because this is the moment the
          product exists for. */}
      <article className="beat beat--turn">
        <p className="beat__time figure">11:51 pm</p>
        <div className="beat__body">
          <h2 className="beat__heading beat__heading--turn">So say it out loud instead.</h2>
          <p className="beat__text">
            Talk for a minute or ten, in whatever order it comes out. That is the whole thing you
            have to do.
          </p>
        </div>
      </article>

      {AFTER.map((beat) => (
        <article className="beat" key={beat.time}>
          <p className="beat__time figure">{beat.time}</p>
          <div className="beat__body">
            <h2 className="beat__heading">{beat.heading}</h2>
            {beat.body.map((line) => (
              <p className="beat__text" key={line.slice(0, 24)}>
                {line}
              </p>
            ))}
          </div>
        </article>
      ))}

      {/* The proof: an entry, rendered as the app renders one. Claiming Pana
          writes well is worth less than one page of it. */}
      <article className="beat">
        <p className="beat__time figure">written</p>
        <div className="beat__body">
          <figure className="entry">
            <figcaption className="entry__head">
              <span className="entry__date">{ENTRY.date}</span>
              <span className="entry__mood">{ENTRY.mood}</span>
            </figcaption>

            <blockquote className="entry__text">{ENTRY.text}</blockquote>

            <div className="entry__actions">
              <p className="entry__actions-title">What the day asked for</p>
              {ENTRY.actions.map((action) => (
                <p className="entry__action" key={action}>
                  <span className="entry__action-mark" aria-hidden="true" />
                  {action}
                </p>
              ))}
            </div>
          </figure>
        </div>
      </article>

      <article className="beat">
        <p className="beat__time figure">a year on</p>
        <div className="beat__body">
          <h2 className="beat__heading">You have the record you meant to keep.</h2>
          <p className="beat__text">
            You did not become a different person. Talking is just something you can still do on
            the days when writing is out of reach, and those are most of them.
          </p>
        </div>
      </article>
    </main>

    {/* --- What it does with what you say ----------------------------------
        Three plain statements about handling someone's private speech. This
        is the section that earns trust, so it makes claims, not promises. */}
    <section className="terms">
      <h2 className="terms__title">What happens to what you say</h2>
      <dl className="terms__list">
        <div className="terms__item">
          <dt className="terms__term">It is yours</dt>
          <dd className="terms__def">
            Your recordings and entries belong to your account. They are not training data and
            they are not read by anyone else.
          </dd>
        </div>
        <div className="terms__item">
          <dt className="terms__term">Delete means delete</dt>
          <dd className="terms__def">
            Remove a recording and its transcript goes with it. Remove the last one for a day and
            that day&rsquo;s entry goes too, because an entry cannot outlive what it was written
            from.
          </dd>
        </div>
        <div className="terms__item">
          <dt className="terms__term">Nothing is posted</dt>
          <dd className="terms__def">
            There is no feed, no streak, and nobody to perform for. A diary that is being watched
            stops being a diary.
          </dd>
        </div>
      </dl>
    </section>

    <section className="close">
      <p className="close__line">Talk tonight. Read it back tomorrow.</p>
      <a className="button button--primary" href={APP_URL}>
        Start talking
      </a>
    </section>

    <footer className="foot">
      <span>Pana</span>
      <a href={APP_URL}>Open Pana</a>
    </footer>
  </div>
);

export default App;
