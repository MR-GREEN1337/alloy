import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import Logo from './Logo';
import { BarChart, AlertTriangle, Zap, BrainCircuit, ShieldCheck, Code2 } from 'lucide-react';
import { LinesPatternCard, LinesPatternCardBody } from './LinesPatternCard';


// Helper component for glowing feature tags
interface FeatureItemProps {
  name: string;
  value: string;
  position: string;
}

const FeatureItem: React.FC<FeatureItemProps> = ({ name, value, position }) => {
  return (
    <div className={`absolute ${position} z-10 group transition-all duration-300 hover:scale-110`}>
      <div className="flex items-center gap-2 relative">
        <div className="relative">
          <div className="w-2 h-2 bg-white rounded-full group-hover:animate-pulse"></div>
          <div className="absolute -inset-1 bg-white/30 rounded-full blur-sm opacity-70 group-hover:opacity-100 transition-opacity duration-300"></div>
        </div>
        <div className="text-white relative">
          <div className="font-medium group-hover:text-white transition-colors duration-300">{name}</div>
          <div className="text-white/70 text-sm group-hover:text-white/80 transition-colors duration-300">{value}</div>
          <div className="absolute -inset-2 bg-white/10 rounded-lg blur-md opacity-70 group-hover:opacity-100 transition-opacity duration-300 -z-10"></div>
        </div>
      </div>
    </div>
  );
};

// The WebGL Lightning component (unchanged internally)
interface LightningProps {
  hue?: number;
  xOffset?: number;
  speed?: number;
  intensity?: number;
  size?: number;
}

const Lightning: React.FC<LightningProps> = ({
  hue = 230,
  xOffset = 0,
  speed = 1,
  intensity = 1,
  size = 1,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let animationFrameId: number;
    const resizeCanvas = () => {
      if (!canvas) return;
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    };
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    const gl = canvas.getContext("webgl");
    if (!gl) {
      console.error("WebGL not supported");
      return;
    }

    const vertexShaderSource = `
      attribute vec2 aPosition;
      void main() {
        gl_Position = vec4(aPosition, 0.0, 1.0);
      }
    `;

    const fragmentShaderSource = `
      precision mediump float;
      uniform vec2 iResolution;
      uniform float iTime;
      uniform float uHue;
      uniform float uXOffset;
      uniform float uSpeed;
      uniform float uIntensity;
      uniform float uSize;
      
      #define OCTAVE_COUNT 10

      vec3 hsv2rgb(vec3 c) {
          vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0,4.0,2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
          return c.z * mix(vec3(1.0), rgb, c.y);
      }

      float hash11(float p) {
          p = fract(p * .1031);
          p *= p + 33.33;
          p *= p + p;
          return fract(p);
      }

      float hash12(vec2 p) {
          vec3 p3 = fract(vec3(p.xyx) * .1031);
          p3 += dot(p3, p3.yzx + 33.33);
          return fract((p3.x + p3.y) * p3.z);
      }

      mat2 rotate2d(float theta) {
          float c = cos(theta);
          float s = sin(theta);
          return mat2(c, -s, s, c);
      }

      float noise(vec2 p) {
          vec2 ip = floor(p);
          vec2 fp = fract(p);
          float a = hash12(ip);
          float b = hash12(ip + vec2(1.0, 0.0));
          float c = hash12(ip + vec2(0.0, 1.0));
          float d = hash12(ip + vec2(1.0, 1.0));
          
          vec2 t = smoothstep(0.0, 1.0, fp);
          return mix(mix(a, b, t.x), mix(c, d, t.x), t.y);
      }

      float fbm(vec2 p) {
          float value = 0.0;
          float amplitude = 0.5;
          for (int i = 0; i < OCTAVE_COUNT; ++i) {
              value += amplitude * noise(p);
              p *= rotate2d(0.45);
              p *= 2.0;
              amplitude *= 0.5;
          }
          return value;
      }

      void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
          vec2 uv = fragCoord / iResolution.xy;
          uv = 2.0 * uv - 1.0;
          uv.x *= iResolution.x / iResolution.y;
          uv.x += uXOffset;
          
          uv += 2.0 * fbm(uv * uSize + 0.8 * iTime * uSpeed) - 1.0;
          
          float dist = abs(uv.x);
          vec3 baseColor = hsv2rgb(vec3(uHue / 360.0, 0.7, 0.8));
          vec3 col = baseColor * pow(mix(0.0, 0.07, hash11(iTime * uSpeed)) / dist, 1.0) * uIntensity;
          col = pow(col, vec3(1.0));
          fragColor = vec4(col, 1.0);
      }

      void main() {
          mainImage(gl_FragColor, gl_FragCoord.xy);
      }
    `;

    const compileShader = (source: string, type: number): WebGLShader | null => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error("Shader compile error:", gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const vertexShader = compileShader(vertexShaderSource, gl.VERTEX_SHADER);
    const fragmentShader = compileShader(fragmentShaderSource, gl.FRAGMENT_SHADER);
    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program linking error:", gl.getProgramInfoLog(program));
      return;
    }
    gl.useProgram(program);

    const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]);
    const vertexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

    const aPosition = gl.getAttribLocation(program, "aPosition");
    gl.enableVertexAttribArray(aPosition);
    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0);

    const iResolutionLocation = gl.getUniformLocation(program, "iResolution");
    const iTimeLocation = gl.getUniformLocation(program, "iTime");
    const uHueLocation = gl.getUniformLocation(program, "uHue");
    const uXOffsetLocation = gl.getUniformLocation(program, "uXOffset");
    const uSpeedLocation = gl.getUniformLocation(program, "uSpeed");
    const uIntensityLocation = gl.getUniformLocation(program, "uIntensity");
    const uSizeLocation = gl.getUniformLocation(program, "uSize");

    const startTime = performance.now();
    const render = () => {
      if (!canvasRef.current) return;
      resizeCanvas();
      gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
      gl.uniform2f(iResolutionLocation, gl.canvas.width, gl.canvas.height);
      const currentTime = performance.now();
      gl.uniform1f(iTimeLocation, (currentTime - startTime) / 1000.0);
      gl.uniform1f(uHueLocation, hue);
      gl.uniform1f(uXOffsetLocation, xOffset);
      gl.uniform1f(uSpeedLocation, speed);
      gl.uniform1f(uIntensityLocation, intensity);
      gl.uniform1f(uSizeLocation, size);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      animationFrameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, [hue, xOffset, speed, intensity, size]);

  return <canvas ref={canvasRef} className="w-full h-full relative" />;
};

const featureList = [
  {
    icon: BarChart,
    title: 'Data-Driven Compatibility Score',
    description: 'Go beyond financials. Our core metric quantifies cultural alignment by analyzing millions of taste-based data points from Qloo\'s AI.',
  },
  {
    icon: AlertTriangle,
    title: 'Culture Clash Identification',
    description: 'Proactively identify potential integration risks. We highlight areas of stark cultural divergence between brand audiences before they become post-merger problems.',
  },
  {
    icon: Zap,
    title: 'Untapped Growth Discovery',
    description: 'Uncover hidden synergies. Alloy pinpoints shared cultural passions, revealing immediate opportunities for joint marketing, product bundling, and cross-promotion.',
  },
  {
    icon: BrainCircuit,
    title: 'AI-Powered Brand Archetyping',
    description: 'Understand the "why" behind the data. Gemini generates a deep, qualitative summary of each brand\'s persona and values based on their cultural DNA.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure & Confidential Analysis',
    description: 'Your strategic analysis is sensitive. Our platform ensures end-to-end security, with robust authentication and data handling for peace of mind.',
  },
  {
    icon: Code2,
    title: 'API-First for Seamless Integration',
    description: 'Built for power users. Integrate Alloy\'s cultural intelligence directly into your existing M&A workflows and proprietary models with our robust API.',
  },
];


export const FeaturesSection = () => (
  <section className="bg-black py-20 sm:py-32">
    <div className="mx-auto max-w-7xl px-6 lg:px-8">
      <div className="mx-auto max-w-2xl lg:text-center">
        <h2 className="text-base font-semibold leading-7 text-blue-400">The Alloy Advantage</h2>
        <p className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">
          De-Risk Deals with Precision Intelligence
        </p>
        <p className="mt-6 text-lg leading-8 text-gray-300">
          Alloy provides a multi-faceted view of cultural compatibility, transforming a traditionally qualitative and high-risk variable into a quantifiable asset.
        </p>
      </div>
      <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
        <dl className="grid max-w-xl grid-cols-1 gap-8 lg:max-w-none lg:grid-cols-3">
          {featureList.map((feature) => (
            <LinesPatternCard 
              key={feature.title} 
              className="flex flex-col bg-neutral-950 border-white/10"
              gradientClassName="from-neutral-950/90 via-neutral-950/40 to-neutral-950/10"
            >
              <LinesPatternCardBody>
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-white">
                  <feature.icon className="h-5 w-5 flex-none text-blue-400" aria-hidden="true" />
                  {feature.title}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-300">
                  <p className="flex-auto">{feature.description}</p>
                </dd>
              </LinesPatternCardBody>
            </LinesPatternCard>
          ))}
        </dl>
      </div>
    </div>
  </section>
);


// The main Alloy Hero Component
export const AlloyHeroSection: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.5,
        ease: "easeOut"
      }
    }
  };

  return (
    <div className="relative w-full min-h-screen bg-black text-white overflow-hidden">
      <div className="relative z-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 h-full flex flex-col">
        {/* Navigation */}
        <motion.nav
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="px-4 backdrop-blur-3xl bg-black/50 rounded-full py-3 flex justify-between items-center"
        >
          <Logo />
          <div className="flex items-center space-x-4">
            <Link href="/login">
              <button className="hidden md:block px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors">Log In</button>
            </Link>
            <Link href="/login">
              <button className="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm hover:bg-white/20 transition-colors">De-Risk Your Deal</button>
            </Link>
            <button
              className="md:hidden p-2 rounded-md focus:outline-none"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
              )}
            </button>
          </div>
        </motion.nav>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="md:hidden fixed inset-0 z-50 bg-black/95 backdrop-blur-lg">
              <div className="flex flex-col items-center justify-center h-full space-y-6 text-lg">
                <button className="absolute top-6 right-6 p-2" onClick={() => setMobileMenuOpen(false)}>
                  <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
                <button className="px-6 py-3">Features</button>
                <button className="px-6 py-3">Pricing</button>
                <button className="px-6 py-3">Case Studies</button>
                <button className="px-6 py-3">Contact</button>
                <Link href="/login" className="px-6 py-3">
                  Log In
                </Link>
                <Link href="/login" className="px-6 py-3 bg-white/10 backdrop-blur-sm rounded-full">
                  De-Risk Your Deal
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Main hero content */}
        <div className="flex-grow flex flex-col items-center justify-center text-center">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="relative z-30 flex flex-col items-center max-w-4xl mx-auto"
          >
            <motion.div
              variants={itemVariants}
              className="flex items-center space-x-2 px-4 py-2 bg-white/5 hover:bg-white/10 backdrop-blur-sm rounded-full text-sm mb-6 transition-all duration-300 group"
            >
              <span>The New Paradigm of Cultural Due Diligence</span>
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="text-5xl md:text-7xl font-light mb-2 tracking-tighter"
            >
              Where Culture Meets Capital
            </motion.h1>

            <motion.h2
              variants={itemVariants}
              className="text-3xl md:text-5xl pb-3 font-light bg-gradient-to-r from-gray-200 via-gray-300 to-gray-400 bg-clip-text text-transparent"
            >
              Quantify Brand Compatibility
            </motion.h2>

            <motion.p
              variants={itemVariants}
              className="text-gray-400 mb-9 max-w-2xl mt-4"
            >
              Alloy is a financial-grade intelligence platform that de-risks multi-billion dollar acquisitions by replacing gut feeling with a data-driven Cultural Compatibility Score.
            </motion.p>

            <Link href="/login">
              <motion.button
                variants={itemVariants}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-colors"
              >
                De-Risk Your Deal
              </motion.button>
            </Link>
          </motion.div>
        </div>
      </div>

      {/* Background elements */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.5 }}
        className="absolute inset-0 z-0"
      >
        <div className="absolute inset-0 bg-black/80"></div>
        <div className="absolute top-[55%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full bg-gradient-to-b from-blue-900/20 to-purple-900/10 blur-3xl"></div>
        
        {/* THE VISUAL METAPHOR: Two distinct data streams representing the two companies being analyzed */}
        <div className="absolute top-0 w-full left-1/2 transform -translate-x-1/2 h-full">
          {/* Stream 1: The Acquirer */}
          <Lightning
            hue={210} // A corporate blue
            xOffset={-0.5}
            speed={0.8}
            intensity={0.4}
            size={2.5}
          />
          {/* Stream 2: The Target */}
          <Lightning
            hue={280} // A different, more creative purple
            xOffset={0.5}
            speed={0.8}
            intensity={0.4}
            size={2.5}
          />
        </div>
      </motion.div>
    </div>
  );
};