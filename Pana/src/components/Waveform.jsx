import React, { useEffect, useMemo, useRef, useState } from 'react';
import '../styles/recorder.css';

const WIDTH = 800;
const HEIGHT = 400;
const SEGMENTS = 20;

/** Amplitude at rest, as a fraction of full. Low enough that speech is a clear
 *  departure from it, high enough that the wave is alive before you start. */
const IDLE = 0.16;

/**
 * The four layers of the wave.
 *
 * Each is the same shape at a different speed, amplitude, frequency, phase and
 * vertical offset, stacked back to front and blurred progressively less. The
 * offsets are what keep them from moving as one body: the parallax between
 * them is the whole illusion of depth.
 */
const LAYERS = [
  { speed: 0.4, amplitude: 100, frequency: 3, phase: 0, offset: -15, fill: 1, filter: 'blur1' },
  { speed: 0.5, amplitude: 90, frequency: 3.5, phase: 0.5, offset: -5, fill: 2, filter: 'blur2' },
  { speed: 0.6, amplitude: 80, frequency: 4, phase: 1, offset: 5, fill: 3, filter: 'blur3' },
  { speed: 0.7, amplitude: 70, frequency: 4.5, phase: 1.5, offset: 15, fill: 4, filter: 'glow' },
];

/**
 * Build one closed wave shape: an upper curve and its inverted mirror, joined.
 *
 * Three sine components at different frequencies are summed so the motion does
 * not read as a single repeating wave, and the whole thing is tapered by a
 * half-sine so it comes to a point at both ends -- that taper is what gives
 * the shape its leaf silhouette rather than a band across the screen.
 */
const wavePath = (t, amplitude, frequency, phase, verticalOffset, intensity) => {
  const centerY = HEIGHT / 2 + verticalOffset;

  const yAt = (i, shift) => {
    const x = i / SEGMENTS;
    const wave1 = Math.sin(x * frequency + t + phase + shift) * amplitude;
    const wave2 = Math.sin(x * frequency * 1.5 + t * 0.7 + phase + shift) * amplitude * 0.4;
    const wave3 = Math.sin(x * frequency * 0.5 + t * 1.3 + phase + shift) * amplitude * 0.3;
    const taper = Math.sin(x * Math.PI);
    return centerY + (wave1 + wave2 + wave3) * taper * intensity;
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

  // The underside is the same wave shifted half a cycle, walked back to the
  // start, which closes the shape into a body rather than a stroke.
  for (let i = SEGMENTS; i >= 0; i -= 1) {
    path += ` L ${(i / SEGMENTS) * WIDTH} ${yAt(i, Math.PI)}`;
  }

  return `${path} Z`;
};

/**
 * The live wave.
 *
 * Four translucent layers drifting against each other, lit from inside. Both
 * the amplitude and the travel speed of all four are scaled by the analyser's
 * level, so the wave swells and quickens when you speak and settles when you
 * stop -- it is the app listening, made visible, rather than an animation that
 * would look the same with the microphone unplugged.
 *
 * At rest it holds a low, slow swell: present, but clearly not hearing
 * anything yet, so that speaking is a visible change rather than a small one.
 *
 * @param {Object} props
 * @param {number[]} [props.audioData] Analyser bytes, 0-255.
 * @param {boolean} [props.isRecording]
 * @param {boolean} [props.isPaused]
 */
const Waveform = ({ audioData = [], isRecording = false, isPaused = false }) => {
  const [time, setTime] = useState(0);
  const live = isRecording && !isPaused;

  // The measured level, eased in a ref so the wave follows the voice smoothly
  // instead of jittering between analyser frames. Kept out of state because it
  // is read inside the animation loop every frame.
  const levelRef = useRef(IDLE);
  const targetRef = useRef(IDLE);
  const [intensity, setIntensity] = useState(IDLE);

  targetRef.current = useMemo(() => {
    if (!live || !audioData.length) return IDLE;

    const average = audioData.reduce((sum, value) => sum + value, 0) / audioData.length;

    // The curve matters more than the range. Speech sits low in the byte range,
    // so a linear map leaves the wave nearly flat while someone is talking;
    // the root opens up the quiet end where the voice actually lives.
    const level = (average / 255) ** 0.55;
    return IDLE + level * (1 - IDLE);
  }, [audioData, live]);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;

    let frame;
    const animate = () => {
      // Ease toward the measured level: rising fast, so the wave answers a
      // syllable, and falling slower, so it settles rather than snapping shut
      // between words.
      const target = targetRef.current;
      const current = levelRef.current;
      levelRef.current = current + (target - current) * (target > current ? 0.35 : 0.08);
      setIntensity(levelRef.current);

      // The wave also travels faster the louder you are. Amplitude alone reads
      // as a bigger shape; speed is what makes it read as energy.
      setTime((t) => t + 0.012 + levelRef.current * 0.05);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(frame);
  }, []);

  // Fixed positions, drifted by the clock: regenerating them each frame would
  // make the sparkles flicker in place instead of floating.
  const sparkles = useMemo(
    () =>
      Array.from({ length: 15 }, () => ({
        cx: 100 + Math.random() * 600,
        cy: 150 + Math.random() * 100,
        r: 2 + Math.random() * 3,
      })),
    [],
  );

  return (
    <div
      className={`wave${live ? ' wave--live' : ''}${isPaused ? ' wave--paused' : ''}`}
      // The light the wave casts rises with the voice, so the whole element
      // brightens as you speak rather than only the shape inside it changing.
      style={live ? { '--wave-glow': intensity.toFixed(3) } : undefined}
    >
      <svg
        className="wave__svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="wave-fill-1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.3)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.4)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.3)" />
          </linearGradient>
          <linearGradient id="wave-fill-2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(79, 209, 197, 0.5)" />
            <stop offset="50%" stopColor="rgba(56, 178, 172, 0.6)" />
            <stop offset="100%" stopColor="rgba(79, 209, 197, 0.5)" />
          </linearGradient>
          <linearGradient id="wave-fill-3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(56, 178, 172, 0.7)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.8)" />
            <stop offset="100%" stopColor="rgba(56, 178, 172, 0.7)" />
          </linearGradient>
          <linearGradient id="wave-fill-4" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.4)" />
            <stop offset="50%" stopColor="rgba(255, 255, 255, 0.35)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.4)" />
          </linearGradient>

          <filter id="blur1" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" />
          </filter>
          <filter id="blur2" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" />
          </filter>
          <filter id="blur3" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
          </filter>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
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
            fill={`url(#wave-fill-${layer.fill})`}
            filter={`url(#${layer.filter})`}
          />
        ))}

        {/* Sparkles fade in with the voice rather than appearing the moment
            recording starts: they are the crest of the wave catching light, so
            they belong to loudness, not to the mode. */}
        {live &&
          intensity > IDLE * 1.6 &&
          sparkles.map((sparkle, i) => (
            <circle
              key={i}
              cx={sparkle.cx + Math.sin(time * 2 + i) * 20}
              cy={sparkle.cy + Math.cos(time * 1.5 + i) * 30}
              r={sparkle.r}
              fill="white"
              opacity={(0.5 + Math.sin(time * 3 + i) * 0.3) * intensity}
              filter="url(#glow)"
            />
          ))}
      </svg>

      {live && <div className="wave__label">Recording...</div>}
    </div>
  );
};

export default Waveform;
