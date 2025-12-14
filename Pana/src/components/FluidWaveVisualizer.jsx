import React, { useEffect, useState, useMemo } from 'react';
import { useSpring, animated } from '@react-spring/web';

const FluidWaveVisualizer = ({ audioData = [], isRecording = false }) => {
  const [time, setTime] = useState(0);

  // Calculate audio intensity
  const intensity = useMemo(() => {
    if (!audioData || audioData.length === 0) return 0.5;
    const avg = audioData.reduce((a, b) => a + b, 0) / audioData.length;
    return isRecording ? Math.min(0.5 + (avg / 255) * 0.5, 1.0) : 0.5;
  }, [audioData, isRecording]);

  // Animation loop
  useEffect(() => {
    let animationId;
    const animate = () => {
      setTime(t => t + 0.02);
      animationId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationId);
  }, []);

  // Generate smooth wave path with bezier curves
  const generateWavePath = (t, amplitude, frequency, phase, verticalOffset) => {
    const width = 800;
    const height = 400;
    const centerY = height / 2 + verticalOffset;
    
    const points = [];
    const segments = 20;
    
    for (let i = 0; i <= segments; i++) {
      const x = (i / segments) * width;
      const normalizedX = i / segments;
      
      // Multiple sine waves for organic movement
      const wave1 = Math.sin(normalizedX * frequency + t + phase) * amplitude;
      const wave2 = Math.sin(normalizedX * frequency * 1.5 + t * 0.7 + phase) * amplitude * 0.4;
      const wave3 = Math.sin(normalizedX * frequency * 0.5 + t * 1.3 + phase) * amplitude * 0.3;
      
      // Taper at edges for organic diamond/leaf shape
      const taper = Math.sin(normalizedX * Math.PI);
      const y = centerY + (wave1 + wave2 + wave3) * taper * intensity;
      
      points.push({ x, y });
    }
    
    // Create smooth bezier path
    let path = `M ${points[0].x} ${points[0].y}`;
    
    for (let i = 1; i < points.length - 1; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const next = points[i + 1];
      
      // Calculate control points for smooth curve
      const cp1x = prev.x + (curr.x - prev.x) * 0.5;
      const cp1y = prev.y + (curr.y - prev.y) * 0.5;
      const cp2x = curr.x + (next.x - curr.x) * 0.5;
      const cp2y = curr.y + (next.y - curr.y) * 0.5;
      
      path += ` Q ${curr.x} ${curr.y} ${(curr.x + next.x) / 2} ${(curr.y + next.y) / 2}`;
    }
    
    // Close the shape (mirror bottom)
    const lastPoint = points[points.length - 1];
    path += ` L ${lastPoint.x} ${lastPoint.y}`;
    
    // Bottom wave (mirrored)
    for (let i = segments; i >= 0; i--) {
      const x = (i / segments) * width;
      const normalizedX = i / segments;
      
      const wave1 = Math.sin(normalizedX * frequency + t + phase + Math.PI) * amplitude;
      const wave2 = Math.sin(normalizedX * frequency * 1.5 + t * 0.7 + phase + Math.PI) * amplitude * 0.4;
      const wave3 = Math.sin(normalizedX * frequency * 0.5 + t * 1.3 + phase + Math.PI) * amplitude * 0.3;
      
      const taper = Math.sin(normalizedX * Math.PI);
      const y = centerY + (wave1 + wave2 + wave3) * taper * intensity;
      
      if (i === segments) {
        path += ` L ${x} ${y}`;
      } else {
        path += ` L ${x} ${y}`;
      }
    }
    
    path += ' Z';
    return path;
  };

  // Generate sparkle positions
  const sparkles = useMemo(() => {
    return Array.from({ length: 15 }, (_, i) => ({
      cx: 100 + Math.random() * 600,
      cy: 150 + Math.random() * 100,
      r: 2 + Math.random() * 3,
      delay: i * 0.1
    }));
  }, []);

  return (
    <div className="wave-container">
      <svg viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet" className="wave-svg">
        <defs>
          {/* Gradients */}
          <linearGradient id="waveGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.3)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.4)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.3)" />
          </linearGradient>
          
          <linearGradient id="waveGradient2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(79, 209, 197, 0.5)" />
            <stop offset="50%" stopColor="rgba(56, 178, 172, 0.6)" />
            <stop offset="100%" stopColor="rgba(79, 209, 197, 0.5)" />
          </linearGradient>
          
          <linearGradient id="waveGradient3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(56, 178, 172, 0.7)" />
            <stop offset="50%" stopColor="rgba(79, 209, 197, 0.8)" />
            <stop offset="100%" stopColor="rgba(56, 178, 172, 0.7)" />
          </linearGradient>
          
          <linearGradient id="waveGradient4" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(129, 230, 217, 0.4)" />
            <stop offset="50%" stopColor="rgba(255, 255, 255, 0.3)" />
            <stop offset="100%" stopColor="rgba(129, 230, 217, 0.4)" />
          </linearGradient>

          {/* Blur filters */}
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

        {/* Layer 1 - Back, most blurred */}
        <path
          d={generateWavePath(time * 0.4, 100, 3, 0, -15)}
          fill="url(#waveGradient1)"
          filter="url(#blur1)"
        />

        {/* Layer 2 */}
        <path
          d={generateWavePath(time * 0.5, 90, 3.5, 0.5, -5)}
          fill="url(#waveGradient2)"
          filter="url(#blur2)"
        />

        {/* Layer 3 - Main body */}
        <path
          d={generateWavePath(time * 0.6, 80, 4, 1, 5)}
          fill="url(#waveGradient3)"
          filter="url(#blur3)"
        />

        {/* Layer 4 - Front highlight */}
        <path
          d={generateWavePath(time * 0.7, 70, 4.5, 1.5, 15)}
          fill="url(#waveGradient4)"
          filter="url(#glow)"
        />

        {/* Sparkles */}
        {isRecording && sparkles.map((sparkle, i) => (
          <circle
            key={i}
            cx={sparkle.cx + Math.sin(time * 2 + i) * 20}
            cy={sparkle.cy + Math.cos(time * 1.5 + i) * 30}
            r={sparkle.r}
            fill="white"
            opacity={0.5 + Math.sin(time * 3 + i) * 0.3}
            filter="url(#glow)"
          />
        ))}
      </svg>

      {isRecording && (
        <div className="recording-text">Recording...</div>
      )}

      <style>{`
        .wave-container {
          position: relative;
          width: 100%;
          height: 300px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .wave-svg {
          width: 100%;
          max-width: 700px;
          height: 100%;
        }

        .recording-text {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          color: white;
          font-size: 1.75rem;
          font-weight: 300;
          letter-spacing: 0.15em;
          text-shadow: 
            0 2px 10px rgba(79, 209, 197, 0.8),
            0 0 30px rgba(79, 209, 197, 0.5),
            0 0 60px rgba(79, 209, 197, 0.3);
          pointer-events: none;
          z-index: 10;
        }
      `}</style>
    </div>
  );
};

export default FluidWaveVisualizer;
