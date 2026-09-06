import React, { useEffect, useMemo, useRef, useState } from 'react';

const WIDTH = 800;
const HEIGHT = 400;
const SEGMENTS = 20;

/**
 * The four layers of the wave, back to front.
 *
 * Each is the same shape at a different speed, amplitude, frequency, phase and
 * vertical offset, blurred progressively less toward the front. The parallax
 * between them is the whole illusion of depth -- moved as one body they would
 * read as a single flat ribbon.
 */
const LAYERS = [
  { speed: 0.4, amplitude: 100, frequency: 3, phase: 0, offset: -15, fill: 1, blur: 'l-blur1' },
  { speed: 0.5, amplitude: 90, frequency: 3.5, phase: 0.5, offset: -5, fill: 2, blur: 'l-blur2' },
  { speed: 0.6, amplitude: 80, frequency: 4, phase: 1, offset: 5, fill: 3, blur: 'l-blur3' },
  { speed: 0.7, amplitude: 70, frequency: 4.5, phase: 1.5, offset: 15, fill: 4, blur: 'l-glow' },
];

/**
 * What the page is "hearing".
 *
 * A real sentence, said the way people actually talk at the end of a day --
 * hedged, self-correcting, trailing off. A clean marketing sentence here would
 * undercut the argument the page is making, which is that you do not have to
 * compose anything.
 */
const SPOKEN =
  'so today was, honestly, kind of a lot, the review went better than I thought and then I walked home the long way';

/** A word every 260ms, then a pause on the finished sentence, then again. */
const WORD_MS = 260;
const HOLD_MS = 2600;

/**
 * One closed wave shape: an upper curve and its inverted mirror, joined.
 *
 * Three sine components at different frequencies are summed so the motion does
 * not read as a single repeating wave, and a half-sine taper pins both ends to
 * the centre line -- that taper is what gives the shape its leaf silhouette
 * rather than a band running off both edges.
 */
const wavePath = (t, amplitude, frequency, phase, verticalOffset, intensity) => {
  const centerY = HEIGHT / 2 + verticalOffset;

  const yAt = (i, shift) => {
    const x = i / SEGMENTS;
    const w1 = Math.sin(x * frequency + t + phase + shift) * amplitude;
    const w2 = Math.sin(x * frequency * 1.5 + t * 0.7 + phase + shift) * amplitude * 0.4;
    const w3 = Math.sin(x * frequency * 0.5 + t * 1.3 + phase + shift) * amplitude * 0.3;
    return centerY + (w1 + w2 + w3) * Math.sin(x * Math.PI) * intensity;
  };

  const points = Array.from({ length: SEGMENTS + 1 }, (_, i) => ({
    x: (i / SEGMENTS) * WIDTH,
    y: yAt(i, 0),
  }));

  // Quadratic segments through the midpoints, which smooths the corners the
  // sampled points would otherwise leave.
  let path = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i += 1) {
    const curr = points[i];
    const next = points[i + 1];
    path += ` Q ${curr.x} ${curr.y} ${(curr.x + next.x) / 2} ${(curr.y + next.y) / 2}`;
  }
  path += ` L ${points[points.length - 1].x} ${points[points.length - 1].y}`;

  // The underside is the same wave half a cycle out, walked back to the start,
  // which closes the shape into a body rather than a stroke.
  for (let i = SEGMENTS; i >= 0; i -= 1) {
    path += ` L ${(i / SEGMENTS) * WIDTH} ${yAt(i, Math.PI)}`;
  }

  return `${path} Z`;
};

/**
 * The hero: the product, running.
 *
 * Rather than describe what Pana does, the page does it -- the wave moves and
 * the words arrive underneath one at a time, the way a transcript actually
 * lands. The wave's amplitude is driven by the same clock that reveals the
 * words, so it swells while the sentence is being said and settles when it
 * stops. That coupling is the point: the sound is producing the text.
 */
const HeroWave = () => {
  const words = useMemo(() => SPOKEN.split(' '), []);
  const [time, setTime] = useState(0);
  const [spokenCount, setSpokenCount] = useState(0);
  const [speaking, setSpeaking] = useState(true);

  // Held in a ref as well as state: the animation loop reads it every frame,
  // and reading state there would close over a stale value.
  const intensityRef = useRef(0.2);
  const [intensity, setIntensity] = useState(0.2);

  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The transcript loop: reveal a word at a time, hold the finished sentence,
  // then clear and start again.
  useEffect(() => {
    if (reduced) {
      setSpokenCount(words.length);
      setSpeaking(false);
      return undefined;
    }

    let timer;

    if (spokenCount < words.length) {
      timer = setTimeout(() => setSpokenCount((n) => n + 1), WORD_MS);
    } else {
      setSpeaking(false);
      timer = setTimeout(() => {
        setSpokenCount(0);
        setSpeaking(true);
      }, HOLD_MS);
    }

    return () => clearTimeout(timer);
  }, [spokenCount, words.length, reduced]);

  useEffect(() => {
    if (reduced) return undefined;

    let frame;
    const animate = () => {
      // While the sentence is being said the target wanders, so the wave has
      // the uneven swell of speech rather than a steady pulse. Rising fast and
      // falling slow is what makes it answer a syllable and settle between
      // them instead of snapping shut.
      const target = speaking ? 0.62 + Math.sin(Date.now() / 220) * 0.28 : 0.16;
      const current = intensityRef.current;
      intensityRef.current = current + (target - current) * (target > current ? 0.2 : 0.05);
      setIntensity(intensityRef.current);
      setTime((t) => t + 0.012 + intensityRef.current * 0.04);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(frame);
  }, [speaking, reduced]);

  return (
    <div className="hero-wave">
      <svg
        className="hero-wave__svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="l-fill-1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.3)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.4)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.3)" />
          </linearGradient>
          <linearGradient id="l-fill-2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(79, 209, 197, 0.5)" />
            <stop offset="50%" stopColor="rgba(56, 178, 172, 0.6)" />
            <stop offset="100%" stopColor="rgba(79, 209, 197, 0.5)" />
          </linearGradient>
          <linearGradient id="l-fill-3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(56, 178, 172, 0.7)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.8)" />
            <stop offset="100%" stopColor="rgba(56, 178, 172, 0.7)" />
          </linearGradient>
          <linearGradient id="l-fill-4" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.4)" />
            <stop offset="50%" stopColor="rgba(255, 255, 255, 0.35)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.4)" />
          </linearGradient>

          <filter id="l-blur1" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" />
          </filter>
          <filter id="l-blur2" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" />
          </filter>
          <filter id="l-blur3" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
          </filter>
          <filter id="l-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {LAYERS.map((layer) => (
          <path
            key={layer.fill}
            d={wavePath(
              time * layer.speed,
              layer.amplitude,
              layer.frequency,
              layer.phase,
              layer.offset,
              intensity,
            )}
            fill={`url(#l-fill-${layer.fill})`}
            filter={`url(#${layer.blur})`}
          />
        ))}
      </svg>

      {/* Set in the prose serif: these are a person's own words, not the
          page's, which is the same rule the app follows for a transcript. */}
      <p className="hero-wave__transcript">
        {words.slice(0, spokenCount).join(' ')}
        {speaking && spokenCount > 0 && <span className="hero-wave__caret" />}
      </p>
    </div>
  );
};

export default HeroWave;
