"use client";
import React, { useEffect, useRef, useState } from "react";

interface LinkItem {
  href: string;
  label: string;
}

interface FooterProps {
  leftLinks: LinkItem[];
  rightLinks: LinkItem[];
  copyrightText: string;
  problemStatement: string;
  solutionStatement: string;
  barCount?: number;
}

const Footer: React.FC<FooterProps> = ({
  leftLinks,
  rightLinks,
  copyrightText,
  problemStatement,
  solutionStatement,
  barCount = 23,
}) => {
  const waveRefs = useRef<(HTMLDivElement | null)[]>([]);
  const footerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const animationFrameRef = useRef<number | null>(null);

  const handleBackToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 },
    );

    if (footerRef.current) {
      observer.observe(footerRef.current);
    }

    return () => {
      if (footerRef.current) {
        observer.unobserve(footerRef.current);
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    let t = 0;

    const animateWave = () => {
      const waveElements = waveRefs.current;
      let offset = 0;

      waveElements.forEach((element, index) => {
        if (element) {
          offset += Math.max(0, 20 * Math.sin((t + index) * 0.3));
          element.style.transform = `translateY(${index + offset}px)`;
        }
      });

      t += 0.1;
      animationFrameRef.current = requestAnimationFrame(animateWave);
    };

    if (isVisible) {
      animateWave();
    } else if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [isVisible]);

  return (
    <footer
      ref={footerRef}
      className="bg-black text-white relative flex flex-col w-full h-full justify-between lg:h-screen select-none"
    >
      <div className="container mx-auto flex flex-col md:flex-row justify-between w-full gap-8 pb-24 pt-16 px-4">
        {/* Left Side */}
        <div className="flex flex-col gap-8 max-w-md">
          <div>
            <h3 className="font-semibold text-lg mb-2">The Problem</h3>
            <p className="text-sm text-gray-400">{problemStatement}</p>
          </div>
          <div>
            <h3 className="font-semibold text-lg mb-2 text-sky-400">The Solution</h3>
            <p className="text-sm text-gray-300">{solutionStatement}</p>
          </div>
          <div className="mt-4">
            <p className="text-sm flex items-center gap-x-1.5">
              <svg className="size-3" viewBox="0 0 80 80">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  fill="currentColor"
                  d="M67.4307 11.5693C52.005 -3.85643 26.995 -3.85643 11.5693 11.5693C-3.85643 26.995 -3.85643 52.005 11.5693 67.4307C26.995 82.8564 52.005 82.8564 67.4307 67.4307C82.8564 52.005 82.8564 26.995 67.4307 11.5693ZM17.9332 17.9332C29.8442 6.02225 49.1558 6.02225 61.0668 17.9332C72.9777 29.8442 72.9777 49.1558 61.0668 61.0668C59.7316 62.4019 58.3035 63.5874 56.8032 64.6232L56.8241 64.6023C46.8657 54.6439 46.8657 38.4982 56.8241 28.5398L58.2383 27.1256L51.8744 20.7617L50.4602 22.1759C40.5018 32.1343 24.3561 32.1343 14.3977 22.1759L14.3768 22.1968C15.4126 20.6965 16.5981 19.2684 17.9332 17.9332ZM34.0282 38.6078C25.6372 38.9948 17.1318 36.3344 10.3131 30.6265C7.56889 39.6809 9.12599 49.76 14.9844 57.6517L34.0282 38.6078ZM21.3483 64.0156C29.24 69.874 39.3191 71.4311 48.3735 68.6869C42.6656 61.8682 40.0052 53.3628 40.3922 44.9718L21.3483 64.0156Z"
                />
              </svg>
              {copyrightText}
            </p>
          </div>
        </div>
        {/* Right Side */}
        <div className="flex flex-col justify-between items-start md:items-end">
          <div className="space-y-4 text-left md:text-right">
             <h3 className="font-semibold text-lg">Features</h3>
            <ul className="flex flex-col items-start md:items-end gap-2">
              {leftLinks.map((link, index) => (
                <li key={index}>
                  <a href={link.href} className="text-sm text-gray-300 hover:text-sky-400">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
             <h3 className="font-semibold text-lg mt-4">Company</h3>
            <ul className="flex flex-col items-start md:items-end gap-2">
              {rightLinks.map((link, index) => (
                <li key={index}>
                  <a href={link.href} className="text-sm text-gray-300 hover:text-sky-400" target="_blank" rel="noopener noreferrer">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <button onClick={handleBackToTop} className="text-sm hover:underline mt-8 md:mt-0">
            Back to top ↑
          </button>
        </div>
      </div>

      <div
        id="waveContainer"
        aria-hidden="true"
        style={{ overflow: "hidden", height: 200 }}
      >
        <div style={{ marginTop: 0 }}>
          {Array.from({ length: barCount }).map((_, index) => (
            <div
              key={index}
              ref={(el) => {
                waveRefs.current[index] = el;
              }}
              className="wave-segment"
              style={{
                height: `${index + 1}px`,
                backgroundColor: "rgb(255, 255, 255)",
                transition: "transform 0.1s ease",
                willChange: "transform",
                marginTop: "-2px",
              }}
            />
          ))}
        </div>
      </div>
    </footer>
  );
};

export default Footer;