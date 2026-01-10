import React from 'react';

const LandingPage = ({ onNavigate }) => {
  return (
    <div className="min-h-screen flex flex-col bg-[#0A0A0A] text-white font-sans">
      {/* Navigation */}
      <nav className="flex justify-between items-center px-4 md:px-8 py-4 md:py-6 bg-[#0A0A0A]/80 backdrop-blur-xl sticky top-0 z-50 border-b border-[#262626]">
        <div className="flex items-center gap-2 md:gap-3 text-lg md:text-xl font-semibold text-white tracking-tight">
          <span className="text-lg md:text-xl">➗</span>
          <span className="hidden sm:inline">MathMentor</span>
        </div>
        <div className="flex gap-4 md:gap-10 items-center">
          <a href="#" className="hidden md:inline text-[#A3A3A3] text-sm font-medium hover:text-white transition-colors duration-200 no-underline">
            Home
          </a>
          <a href="#" className="hidden md:inline text-[#A3A3A3] text-sm font-medium hover:text-white transition-colors duration-200 no-underline">
            Methodology
          </a>
          <button 
            className="bg-white text-[#0A0A0A] px-4 md:px-5 py-2 md:py-2.5 rounded-md font-semibold text-xs md:text-sm border border-white cursor-pointer transition-all duration-200 hover:bg-transparent hover:text-white"
            onClick={onNavigate}
          >
            Dashboard
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 md:px-8 py-16 md:py-32 relative overflow-hidden">
        {/* Background Glow */}
        <div className="absolute w-[400px] md:w-[600px] h-[400px] md:h-[600px] bg-[radial-gradient(circle,rgba(99,102,241,0.15)_0%,rgba(10,10,10,0)_70%)] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-0 pointer-events-none"></div>

        <div className="z-10 max-w-[900px] flex flex-col items-center">
          <div className="inline-flex items-center bg-[#171717] text-indigo-500 px-3 md:px-4 py-1 md:py-1.5 rounded-full text-[10px] md:text-xs font-medium mb-6 md:mb-8 border border-[#262626] tracking-wide">
            AI-Powered Personal Tutor v2.0
          </div>

          <h1 className="text-4xl md:text-6xl lg:text-[4.5rem] leading-[1.1] font-bold mb-4 md:mb-6 text-white tracking-tight px-4">
            Master Complexity. <br />
            <span className="text-[#A3A3A3]">Solve with Clarity.</span>
          </h1>

          <p className="text-base md:text-xl text-[#A3A3A3] max-w-[600px] mb-8 md:mb-12 leading-relaxed font-normal px-4">
            An intelligent reasoning engine designed for JEE-level mathematics.
            Upload problems, visualize concepts, and refine your logic step-by-step.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 md:gap-6 w-full sm:w-auto px-4">
            <button 
              className="bg-white text-[#0A0A0A] px-6 md:px-8 py-3 md:py-4 rounded-md font-semibold text-sm md:text-base sm:min-w-[160px] border border-white cursor-pointer transition-all duration-200 hover:bg-transparent hover:text-white"
              onClick={onNavigate}
            >
              Start Learning
            </button>
            <button className="bg-transparent text-[#A3A3A3] border border-[#262626] px-6 md:px-8 py-3 md:py-4 rounded-md font-medium text-sm md:text-base cursor-pointer transition-all duration-200 hover:text-white hover:border-[#A3A3A3] hover:bg-white/5">
              View Documentation
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
