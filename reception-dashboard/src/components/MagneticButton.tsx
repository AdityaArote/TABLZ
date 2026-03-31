"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";

interface MagneticButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "tertiary";
}

export function MagneticButton({ 
  children, 
  variant = "primary", 
  className = "", 
  ...props 
}: MagneticButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  useEffect(() => {
    const btn = buttonRef.current;
    if (!btn) return;

    const ctx = gsap.context(() => {
      // Hover animation logic
      const xTo = gsap.quickTo(btn, "x", { duration: 1, ease: "elastic.out(1, 0.3)" });
      const yTo = gsap.quickTo(btn, "y", { duration: 1, ease: "elastic.out(1, 0.3)" });

      btn.addEventListener("mousemove", (e) => {
        const { clientX, clientY } = e;
        const { height, width, left, top } = btn.getBoundingClientRect();
        const x = clientX - (left + width / 2);
        const y = clientY - (top + height / 2);
        xTo(x * 0.2);
        yTo(y * 0.2);
      });

      btn.addEventListener("mouseleave", () => {
        xTo(0);
        yTo(0);
      });
    }, buttonRef);

    return () => ctx.revert();
  }, []);

  const baseClasses = "relative overflow-hidden inline-flex items-center justify-center font-sans tracking-wide transition-all duration-300 transform rounded-2xl";
  
  const variants = {
    primary: "bg-gradient-to-br from-primary to-primary-container text-on-primary shadow-lg hover:scale-[1.03]",
    secondary: "bg-transparent border border-outline-variant text-primary hover:bg-surface-lowest hover:border-primary/50 hover:scale-[1.03]",
    tertiary: "bg-transparent text-on-surface-variant hover:text-primary",
  };

  return (
    <button
      ref={buttonRef}
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
    >
      <span className="relative z-10 px-6 py-3">{children}</span>
    </button>
  );
}
