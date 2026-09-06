import React, { useEffect, useRef, useState } from 'react';
import '../styles/recorder.css';

/** Points across the field. Enough to read as a fluid curve, few enough to stay smooth. */
const POINTS = 64;

/** How far a value may move toward its target per frame. Below 1 it eases. */
const EASE = 0.28;

/**
 * The live wave.
 *
 * Two mirrored curves, filled with a teal gradient, breathing around a centre
 * line. The shape is the old visualiser's -- it is the most characteristic
 * thing on the screen and worth keeping -- but the amplitude comes from the
 * analyser rather than from a clock. That matters: a wave driven by time looks
 * identical whether the microphone is open or dead, which is the one thing this
 * control exists to tell you.
 *
 * At rest it does not go flat. A slow shallow swell says the instrument is
 * listening; a flat line would read as broken.
 *
 * @param {Object} props
 * @param {number[]} [props.audioData] Analyser bytes, 0-255.
 * @param {boolean} [props.isRecording]
 * @param {boolean} [props.isPaused]
 */
const Waveform = ({ audioData = [], isRecording = false, isPaused = false }) => {
  const live = isRecording && !isPaused;

  // Amplitudes are held in a ref and eased toward their target every frame, so
  // the curve flows instead of snapping between analyser samples.
  const valuesRef = useRef(new Array(POINTS).fill(0));
  const dataRef = useRef(audioData);
  const liveRef = useRef(live);
  const [path, setPath] = useState({ top: '', mirror: '' });

  dataRef.current = audioData;
  liveRef.current = live;

  useEffect(() => {
    let frame;
    let t = 0;

    const tick = () => {
      t += 0.05;
      const data = dataRef.current;
      const isLive = liveRef.current;
      const values = valuesRef.current;

      for (let i = 0; i < POINTS; i += 1) {
        let target;

        if (isLive && data.length) {
          // The top of the analyser's range carries almost no energy in speech,
          // so only the lower two-thirds is sampled; the rest is hiss.
          const usable = Math.floor(data.length * 0.66);
          const perPoint = Math.max(1, Math.floor(usable / POINTS));
          let sum = 0;
          for (let j = 0; j < perPoint; j += 1) sum += data[i * perPoint + j] ?? 0;
          const level = sum / perPoint / 255;

          // A gentle envelope keeps the ends of the wave tethered to the centre
          // line, which is what gives the shape its fluid taper.
          const envelope = Math.sin((i / (POINTS - 1)) * Math.PI);
          target = level ** 0.7 * envelope;
        } else {
          // Idle: a slow travelling swell, small enough to read as breathing.
          target = (Math.sin(t + i * 0.22) * 0.5 + 0.5) * 0.06;
        }

        values[i] += (target - values[i]) * EASE;
      }

      setPath(buildPaths(values));
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  const className = `recorder__wave${
    live ? ' recorder__wave--live' : isPaused ? ' recorder__wave--paused' : ''
  }`;

  return (
    <div className={className} aria-hidden="true">
      <svg
        className="recorder__wave-svg"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        focusable="false"
      >
        <defs>
          <linearGradient id="wave-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--wave-edge)" />
            <stop offset="50%" stopColor="var(--wave-core)" />
            <stop offset="100%" stopColor="var(--wave-edge)" />
          </linearGradient>
        </defs>
        <path className="recorder__wave-body" d={path.mirror} fill="url(#wave-fill)" />
        <path className="recorder__wave-edge" d={path.top} fill="none" />
      </svg>
    </div>
  );
};

/**
 * Turn amplitudes into two SVG paths in a 0-100 box: the upper curve on its
 * own (drawn as a stroke) and the closed shape mirrored about the centre line
 * (drawn as a fill).
 */
function buildPaths(values) {
  const stepX = 100 / (POINTS - 1);
  const upper = [];
  const lower = [];

  for (let i = 0; i < POINTS; i += 1) {
    const x = i * stepX;
    const half = values[i] * 46; // 46 leaves a little air at the top and bottom
    upper.push(`${x.toFixed(2)},${(50 - half).toFixed(2)}`);
    lower.push(`${x.toFixed(2)},${(50 + half).toFixed(2)}`);
  }

  const top = `M${upper.join(' L')}`;
  const mirror = `${top} L${lower.reverse().join(' L')} Z`;
  return { top, mirror };
}

export default Waveform;
