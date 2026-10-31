"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SLIDES = [
  {
    eyebrow: "Новинка",
    title: "iPhone 16 Pro",
    text: "Титановый корпус, камера с пятикратным зумом и чип A18 Pro.",
    cta: "Купить от 599 990 ₸",
    href: "/product/apple-iphone-16-pro",
    image: "/mock/products/apple-iphone-16-pro-2.svg",
    tone: "from-indigo-600 to-violet-600",
  },
  {
    eyebrow: "Скидка 10%",
    title: "Тишина, которую слышно",
    text: "Sony WH-1000XM5 с эталонным шумоподавлением и 30 часами работы.",
    cta: "Смотреть наушники",
    href: "/catalog/headphones",
    image: "/mock/products/sony-wh-1000xm5-2.svg",
    tone: "from-slate-800 to-slate-600",
  },
  {
    eyebrow: "Игры",
    title: "Готовы к следующему уровню",
    text: "Консоли, геймпады и аксессуары — всё для игр в одном месте.",
    cta: "В раздел «Игры»",
    href: "/catalog/gaming",
    image: "/mock/products/sony-playstation-5-slim-2.svg",
    tone: "from-fuchsia-600 to-rose-500",
  },
];

const INTERVAL = 6000;

export function Hero() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  // Первый слайд рендерится сразу видимым (в том числе на сервере) — анимация только при смене.
  const [changed, setChanged] = useState(false);
  const reduceMotion = useReducedMotion();
  const slide = SLIDES[index];
  const animate = changed && !reduceMotion;

  const show = (next: number) => {
    setChanged(true);
    setIndex((next + SLIDES.length) % SLIDES.length);
  };

  useEffect(() => {
    if (paused || reduceMotion) return;
    const timer = setTimeout(() => {
      setChanged(true);
      setIndex((i) => (i + 1) % SLIDES.length);
    }, INTERVAL);
    return () => clearTimeout(timer);
  }, [index, paused, reduceMotion]);

  const go = (delta: number) => show(index + delta);

  return (
    <section
      aria-roledescription="карусель"
      aria-label="Акции и новинки"
      className="relative overflow-hidden rounded-3xl"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={index}
          initial={animate ? { opacity: 0, x: 24 } : false}
          animate={{ opacity: 1, x: 0 }}
          exit={animate ? { opacity: 0, x: -24 } : undefined}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className={cn(
            "grid min-h-[340px] items-center gap-6 bg-linear-to-br p-6 text-white sm:p-10 md:grid-cols-2 md:p-12",
            slide.tone,
          )}
          aria-roledescription="слайд"
          aria-label={`${index + 1} из ${SLIDES.length}`}
        >
          <div className="relative z-10 max-w-md space-y-4">
            <span className="inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-semibold tracking-wide uppercase backdrop-blur">
              {slide.eyebrow}
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">
              {slide.title}
            </h1>
            <p className="text-base text-white/80 sm:text-lg">{slide.text}</p>
            <Button asChild size="lg" className="bg-white text-slate-900 hover:bg-white/90">
              <Link href={slide.href}>
                {slide.cta} <ArrowRight />
              </Link>
            </Button>
          </div>
          <div className="relative mx-auto aspect-square w-full max-w-[300px] overflow-hidden rounded-[2rem] shadow-2xl shadow-black/20 md:max-w-[340px]">
            <Image
              src={slide.image}
              alt=""
              fill
              priority={index === 0}
              sizes="340px"
              className="object-cover"
            />
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="absolute right-6 bottom-6 flex items-center gap-2">
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={() => go(-1)}
          className="bg-white/15 text-white hover:bg-white/25"
          aria-label="Предыдущий слайд"
        >
          <ChevronLeft />
        </Button>
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={() => go(1)}
          className="bg-white/15 text-white hover:bg-white/25"
          aria-label="Следующий слайд"
        >
          <ChevronRight />
        </Button>
      </div>
      <div className="absolute bottom-7 left-6 flex gap-1.5 sm:left-10 md:left-12">
        {SLIDES.map((s, i) => (
          <button
            key={s.title}
            type="button"
            onClick={() => show(i)}
            aria-label={`Слайд ${i + 1}`}
            aria-current={i === index}
            className={cn(
              "h-1.5 rounded-full bg-white/40 transition-all",
              i === index ? "w-8 bg-white" : "w-1.5",
            )}
          />
        ))}
      </div>
    </section>
  );
}
