"use client"

import { AlloyHeroSection, FeaturesSection } from '@/components/global/Hero'
import React from 'react'
import Footer from '@/components/global/Footer'

function page() {

    const footerLeftLinks = [
      { href: "#", label: "Affinity Overlap Score" },
      { href: "#", label: "Culture Clash Report" },
      { href: "#", label: "Untapped Growth Analysis" },
      { href: "#", label: "AI-Powered Brand Archetyping" },
    ];
    const footerRightLinks = [
      { href: "/login", label: "Log In" },
      { href: "/login", label: "Request a Demo" },
      { href: "https://devpost.com/software/alloy-cultural-due-diligence", label: "Devpost Hackathon Submission" },
    ];
    const problemStatement = "M&A failures are costly, often rooted in unforeseen cultural clashes. Billions are lost when executive 'gut feel' misses the mark on brand incompatibility.";
    const solutionStatement = "Alloy replaces guesswork with data. We provide a quantifiable Cultural Compatibility Score by analyzing audience taste profiles, de-risking acquisitions and illuminating the human element of a deal.";
  
  return (
    <>
      <AlloyHeroSection />
      <FeaturesSection />
      <Footer
        leftLinks={footerLeftLinks}
        rightLinks={footerRightLinks}
        copyrightText="The Cultural Due Diligence Platform."
        problemStatement={problemStatement}
        solutionStatement={solutionStatement}
      />
    </>
  )
}

export default page