"use client";
import React, { useEffect, useRef, useState } from "react";
import Logo from "./Logo";

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
            <div className="text-sm flex items-center gap-x-1.5">
              <Logo />
              {copyrightText}
            </div>
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