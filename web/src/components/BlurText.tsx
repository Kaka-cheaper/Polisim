/**
 * BlurText — 逐词模糊淡入动画组件（适配自 motionsites.ai 设计语言）。
 *
 * 使用 IntersectionObserver 触发 + motion/react stagger 动画。
 * 每个词从 blur(10px) + opacity(0) + y(20px) 动画到清晰可见。
 */
import { useRef, useState, useEffect } from "react";
import { motion } from "motion/react";

interface BlurTextProps {
  text: string;
  className?: string;
  /** 每词动画延迟（ms） */
  delay?: number;
  /** 是否使用 italic */
  italic?: boolean;
}

export default function BlurText({
  text,
  className = "",
  delay = 100,
  italic = false,
}: BlurTextProps) {
  const containerRef = useRef<HTMLHeadingElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const words = text.split(" ");

  return (
    <h1
      ref={containerRef}
      className={`${className} ${italic ? "italic" : ""}`}
    >
      {words.map((word, i) => (
        <motion.span
          key={`${word}-${i}`}
          className="inline-block mr-[0.25em]"
          initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
          animate={
            isVisible
              ? { filter: "blur(0px)", opacity: 1, y: 0 }
              : { filter: "blur(10px)", opacity: 0, y: 20 }
          }
          transition={{
            duration: 0.5,
            delay: i * (delay / 1000),
            ease: [0.16, 1, 0.3, 1],
          }}
        >
          {word}
        </motion.span>
      ))}
    </h1>
  );
}
