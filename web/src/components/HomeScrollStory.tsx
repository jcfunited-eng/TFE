"use client";

import Link from "next/link";
import { Cinzel, Orbitron, Zen_Old_Mincho } from "next/font/google";
import { useEffect, useRef, useState } from "react";
import styles from "./HomeScrollStory.module.css";

type HomeScrollStoryProps = {
  backgroundImage: string;
};

type SignalOriginClass = "signalFromNorthWest" | "signalFromNorthEast" | "signalFromWest" | "signalFromEast" | "signalFromSouth";

type SignalCardClass = "signalTicker" | "signalBarIntegrity" | "signalPriceStructure" | "signalPlainLanguage" | "signalWhatIf";

type SignalStream = {
  label: string;
  origin: SignalOriginClass;
  cardClass: SignalCardClass;
  imageSrc: string;
};

type ChapterThreeFrame = {
  step: string;
  actLabel: string;
  title: string;
  subtitle: string;
  detail: string;
  imageSrc: string;
  iconSrc: string;
};

const displaySerif = Zen_Old_Mincho({
  subsets: ["latin"],
  weight: ["700", "900"],
});

const metallicSerif = Cinzel({
  subsets: ["latin"],
  weight: ["700"],
});

const neonTech = Orbitron({
  subsets: ["latin"],
  weight: ["700"],
});

const HERO_STORY_VIDEO_SRC = "/uploads/home-story-1.mp4";
const CHAPTER_FOUR_VIDEO_SRC = "/uploads/Chapter4AIinAction.mp4";

const CHAPTER_TWO_WORDS = ["Investment", "Research", "Simplified"];

const ACT_ONE_SCAN_COPY =
  'TFE Performs a Market Scan and filters out that significant portion of the stock market that consists of companies that are either "dead money" (no growth), "zombie companies" (struggling to cover debt), or penny stocks that rarely yield long-term value and marks them simply as Avoid.';

const ACT_TWO_RESEARCH_ONLY_COPY = "TFE is for Research Only...";
const ACT_TWO_COIN_RESULT_COPY = "All Investments have risk. Talk with your Broker!";
const ACT_TWO_BROKAGE_COPY = "TFE is not a Brokage Site";

const ACT_THREE_RECOMMENDATIONS_COPY =
  "Daily scans across market cap, volume profile, and momentum signals surface candidates showing buy-side setups in Equities, ETFs, Index, and Crypto.";
const ACT_THREE_UNBIASED_COPY = "Signal-based. No opinions.";
const ACT_THREE_WATCHLIST_COPY =
  "Add any candidate to your Watchlist to track price action and signal changes over time — a clean starting point for conversations with your broker.";
const ACT_THREE_WATCHLIST_MAINTAIN_COPY = "Track signals, not just prices.";
const ACT_FOUR_PORTFOLIO_COPY =
  "Model your positions before you commit. Add assets, adjust lot sizes, and watch your allocation shift in real time.";
const ACT_FOUR_OVERLINE_COPY = "What-if analysis. No execution, no broker access.";
const CHAPTER_FOUR_NEON_COPY =
  "TFE is a proprietary new class of experimental AI. It is not machine learning, and it is not an algorithm. It's new and as such it is much riskier than more established tech, so you use this site at your own risk! More to come...";

const SIGNAL_STREAMS: SignalStream[] = [
  {
    label: "Ticker Inputs",
    origin: "signalFromNorthWest",
    cardClass: "signalTicker",
    imageSrc: "/uploads/TickerInputsflyin.png",
  },
  {
    label: "Bar Integrity",
    origin: "signalFromNorthEast",
    cardClass: "signalBarIntegrity",
    imageSrc: "/uploads/BarIntegrityflyin.png",
  },
  {
    label: "Price Structure",
    origin: "signalFromWest",
    cardClass: "signalPriceStructure",
    imageSrc: "/uploads/ProprietAIflyin.png",
  },
  {
    label: "Plain Language",
    origin: "signalFromEast",
    cardClass: "signalPlainLanguage",
    imageSrc: "/uploads/Plainlanguageflyin.png",
  },
  {
    label: "What-If Portfolio Tool",
    origin: "signalFromSouth",
    cardClass: "signalWhatIf",
    imageSrc: "/uploads/Whatifflyin.png",
  },
];

const CHAPTER_THREE_FRAMES: ChapterThreeFrame[] = [
  {
    step: "01",
    actLabel: "Act 01",
    title: "Scan Universe",
    subtitle: "Filter for integrity-first candidates",
    detail: "Pre-filter symbols, rank opportunity, and remove low-integrity noise before analysis starts.",
    imageSrc: "/uploads/Act1MarketScanFilter.png",
    iconSrc: "/uploads/Act1iconGlass.png",
  },
  {
    step: "02",
    actLabel: "Act 02",
    title: "Compare Signals",
    subtitle: "Read context before commitment",
    detail: "Review signal evidence side-by-side so trend pressure and setup quality are clear before entry.",
    imageSrc: "/uploads/Act2Compare.png",
    iconSrc: "/uploads/Act2iconGlass.png",
  },
  {
    step: "03",
    actLabel: "Act 03",
    title: "Track Watchlist",
    subtitle: "Keep priority aligned with live structure",
    detail: "Promote top candidates into a focused queue while preserving rationale and current status.",
    imageSrc: "/uploads/1771021004354-watchlist-watchlistpage.png",
    iconSrc: "/uploads/Act3iconGlass.png",
  },
  {
    step: "04",
    actLabel: "Act 04",
    title: "Run What-If",
    subtitle: "Model portfolio risk before action",
    detail: "Simulate lot-level changes and allocation shifts to confirm risk balance before execution.",
    imageSrc: "/uploads/Act4Portfolio.png",
    iconSrc: "/uploads/Act4iconGlass.png",
  },
];

const FOOTER_LINK_GROUPS = [
  {
    title: "Get Start",
    links: [
      { label: "Sign Up", href: "/sign-in" },
      { label: "Login", href: "/sign-in" },
    ],
  },
  {
    title: "Discover",
    links: [
      { label: "Recommendations", href: "/recommendations" },
      { label: "Watchlist", href: "/watchlist" },
      { label: "Portfolio", href: "/portfolio-advisor" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/account" },
      { label: "Promotions", href: "/account" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Cookie Policy", href: "/legal" },
      { label: "Privacy Policy", href: "/legal" },
      { label: "Terms and Conditions", href: "/legal" },
      { label: "Disclaimers", href: "/legal" },
    ],
  },
  {
    title: "Help",
    links: [
      { label: "FAQ", href: "/help" },
      { label: "Support", href: "/support" },
      { label: "Release Notes", href: "/help" },
    ],
  },
];

export default function HomeScrollStory({ backgroundImage }: HomeScrollStoryProps) {
  const chapterRefs = useRef<Array<HTMLElement | null>>([]);
  const visibilityRef = useRef<number[]>([]);
  const heroVideoRef = useRef<HTMLVideoElement | null>(null);
  const chapterFourVideoRef = useRef<HTMLVideoElement | null>(null);

  const [activeChapter, setActiveChapter] = useState(0);
  const [activeChapterThreeIndex, setActiveChapterThreeIndex] = useState(0);
  const [chapterThreeReplaySeed, setChapterThreeReplaySeed] = useState(0);
  const [chapterThreeIsPlaying, setChapterThreeIsPlaying] = useState(false);
  const [chapterThreeIsPaused, setChapterThreeIsPaused] = useState(false);
  const [chapterFourReplaySeed, setChapterFourReplaySeed] = useState(0);
  const [chapterTwoWordIndex, setChapterTwoWordIndex] = useState(0);

  useEffect(() => {
    let lastBestIndex = 0;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const target = entry.target as HTMLElement;
          const index = Number(target.dataset.chapterIndex ?? "0");
          visibilityRef.current[index] = entry.isIntersecting ? entry.intersectionRatio : 0;
        }

        let bestIndex = 0;
        let bestRatio = -1;

        for (let i = 0; i < visibilityRef.current.length; i += 1) {
          const ratio = visibilityRef.current[i] ?? 0;
          if (ratio > bestRatio) {
            bestRatio = ratio;
            bestIndex = i;
          }
        }

        if (bestIndex !== lastBestIndex) {
          if (bestIndex === 1) {
            setChapterTwoWordIndex(0);
          }

          if (bestIndex === 2) {
            setActiveChapterThreeIndex(0);
            setChapterThreeIsPaused(false);
            setChapterThreeIsPlaying(true);
            setChapterThreeReplaySeed((seed) => seed + 1);
          }

          lastBestIndex = bestIndex;
        }

        setActiveChapter(bestIndex);
      },
      {
        threshold: [0.2, 0.35, 0.55, 0.75],
        rootMargin: "-12% 0px -12% 0px",
      },
    );

    for (const ref of chapterRefs.current) {
      if (ref) observer.observe(ref);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (activeChapter !== 2 || !chapterThreeIsPlaying || chapterThreeIsPaused) return;

    const lastFrameIndex = CHAPTER_THREE_FRAMES.length - 1;
    const activeFrame = CHAPTER_THREE_FRAMES[activeChapterThreeIndex];
    const actDurationMs = activeFrame?.step === "03" ? 36000 : 14000;

    if (activeChapterThreeIndex >= lastFrameIndex) {
      const stopTimer = window.setTimeout(() => {
        setChapterThreeIsPlaying(false);
        setChapterThreeIsPaused(false);
      }, 0);

      return () => {
        window.clearTimeout(stopTimer);
      };
    }

    const timer = window.setTimeout(() => {
      setActiveChapterThreeIndex((prev) => {
        const next = Math.min(prev + 1, lastFrameIndex);
        if (next >= lastFrameIndex) {
          setChapterThreeIsPlaying(false);
          setChapterThreeIsPaused(false);
        }
        return next;
      });
    }, actDurationMs);

    return () => {
      window.clearTimeout(timer);
    };
  }, [activeChapter, activeChapterThreeIndex, chapterThreeIsPaused, chapterThreeIsPlaying]);

  useEffect(() => {
    if (activeChapter !== 1) return;

    const timer = window.setInterval(() => {
      setChapterTwoWordIndex((prev) => (prev + 1) % CHAPTER_TWO_WORDS.length);
    }, 2200);

    return () => window.clearInterval(timer);
  }, [activeChapter]);

  useEffect(() => {
    const element = heroVideoRef.current;
    if (!element) return;
    const videoEl: HTMLVideoElement = element;

    function ensurePlay() {
      void videoEl.play().catch(() => {
        // Browser policy may block autoplay until interaction.
      });
    }

    function handleVisibilityChange() {
      if (document.hidden) {
        videoEl.pause();
      } else if (!videoEl.ended) {
        ensurePlay();
      }
    }

    videoEl.loop = false;
    videoEl.muted = true;
    videoEl.defaultMuted = true;
    videoEl.playsInline = true;
    videoEl.preload = "auto";

    ensurePlay();
    videoEl.addEventListener("loadeddata", ensurePlay);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      videoEl.removeEventListener("loadeddata", ensurePlay);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    const element = chapterFourVideoRef.current;
    if (!element) return;
    const videoEl: HTMLVideoElement = element;

    videoEl.loop = false;
    videoEl.muted = true;
    videoEl.defaultMuted = true;
    videoEl.playsInline = true;
    videoEl.preload = "auto";
    videoEl.currentTime = 0;

    if (activeChapter !== 3) {
      videoEl.pause();
      return;
    }

    void videoEl.play().catch(() => {
      // Browser policy may block autoplay until interaction.
    });
  }, [activeChapter, chapterFourReplaySeed]);

  function chapterClass(index: number, chapterStyle: string): string {
    return `${styles.chapter} ${chapterStyle} ${activeChapter === index ? styles.chapterActive : ""}`;
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function restartChapterFourExperience() {
    if (activeChapter !== 3) {
      chapterRefs.current[3]?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setChapterFourReplaySeed((seed) => seed + 1);
  }

  function startChapterThreeSequence(stepIndex: number) {
    setActiveChapterThreeIndex(stepIndex);
    setChapterThreeIsPaused(false);
    setChapterThreeIsPlaying(true);
    setChapterThreeReplaySeed((seed) => seed + 1);
  }

  function toggleChapterThreePause() {
    if (chapterThreeIsPaused) {
      setChapterThreeIsPaused(false);
      setChapterThreeIsPlaying(true);
      return;
    }

    if (chapterThreeIsPlaying) {
      setChapterThreeIsPaused(true);
    }
  }

  const activeChapterThree = CHAPTER_THREE_FRAMES[activeChapterThreeIndex];
  const isActOneFrame = activeChapterThree.step === "01";
  const isActTwoFrame = activeChapterThree.step === "02";
  const isActThreeFrame = activeChapterThree.step === "03";
  const isActFourFrame = activeChapterThree.step === "04";
  const chapterThreePauseDisabled = !chapterThreeIsPlaying && !chapterThreeIsPaused;
  const chapterThreePausedClass = chapterThreeIsPaused ? styles.jetonStagePaused : "";

  return (
    <div className={`${styles.storyRoot} ${displaySerif.className}`} style={{ ["--story-bg-image" as string]: `url("${backgroundImage}")` }}>
      <Link
        href="/sign-in"
        className={styles.loginGlassLink}
        aria-label="Open sign in page"
        style={{ width: "clamp(178px, 20vw, 296px)", height: "clamp(62px, 7vw, 104px)" }}
      >
        <img src="/uploads/LoginClearGlass.png" alt="" aria-hidden="true" className={styles.glassIconImage} />
        <span className={styles.srOnly}>Login</span>
      </Link>

      <button
        type="button"
        className={styles.homeGlassButton}
        onClick={scrollToTop}
        aria-label="Back to top"
        style={{ width: "clamp(82px, 7.6vw, 132px)", height: "clamp(82px, 7.6vw, 132px)" }}
      >
        <img src="/uploads/HomeClearGlass.png" alt="" aria-hidden="true" className={styles.glassIconImage} />
        <span className={styles.srOnly}>Back to top</span>
      </button>

      <button
        type="button"
        className={styles.chapterFourReplayGlassButton}
        onClick={restartChapterFourExperience}
        aria-label="Restart chapter 4 experience"
        style={{ width: "clamp(82px, 7.6vw, 132px)", height: "clamp(82px, 7.6vw, 132px)" }}
      >
        <img src="/uploads/ResetClearGlass.png" alt="" aria-hidden="true" className={styles.glassIconImage} />
        <span className={styles.srOnly}>Restart chapter 4 experience</span>
      </button>

      <section
        ref={(el) => {
          chapterRefs.current[0] = el;
        }}
        data-chapter-index="0"
        className={chapterClass(0, styles.chapterHero)}
      >
        <div className={styles.heroVideoLayer} aria-hidden="true">
          <video
            ref={heroVideoRef}
            className={styles.heroVideo}
            poster={backgroundImage}
            autoPlay
            muted
            playsInline
            preload="auto"
            style={{ filter: "contrast(1.06) saturate(1.04) brightness(1)", transform: "translate3d(0,0,0)" }}
          >
            <source src={HERO_STORY_VIDEO_SRC} type="video/mp4" />
          </video>
        </div>

        <div className={styles.heroContent}>
          <h1
            style={{
              fontSize: "clamp(2.35rem, 5.6vw, 5.15rem)",
              color: "#ffffff",
              textShadow: "0 12px 36px rgba(0, 0, 0, 0.7), 0 4px 10px rgba(0, 0, 0, 0.55)",
              lineHeight: 0.9,
            }}
          >
            Calm Signals
            <br />
            Better Decisions
          </h1>

          <p
            className={`${styles.heroTagline} ${metallicSerif.className}`}
            style={{
              background: "none",
              WebkitBackgroundClip: "border-box",
              backgroundClip: "border-box",
              color: "#315f3d",
              WebkitTextFillColor: "#315f3d",
              WebkitTextStroke: "0",
              textShadow: "0 2px 8px rgba(7, 24, 13, 0.34)",
            }}
          >
            Let TFE help you with your Investment Research
          </p>
        </div>
      </section>

      <section
        ref={(el) => {
          chapterRefs.current[1] = el;
        }}
        data-chapter-index="1"
        className={chapterClass(1, styles.chapterSignals)}
      >
        <div className={styles.signalField}>
          {SIGNAL_STREAMS.map((stream, index) => (
            <article
              key={stream.label}
              className={`${styles.signalImageCard} ${styles[stream.origin]} ${styles[stream.cardClass]} ${activeChapter === 1 ? styles.signalImageCardActive : ""}`}
              style={{ ["--signal-delay" as string]: `${index * 1700}ms` }}
              aria-label={stream.label}
            >
              <img src={stream.imageSrc} alt={stream.label} className={styles.signalImage} />
            </article>
          ))}
        </div>

        <div className={styles.centerWordsOnly} aria-live="polite" aria-atomic="true">
          <span key={CHAPTER_TWO_WORDS[chapterTwoWordIndex]} className={styles.wordPulse}>
            {CHAPTER_TWO_WORDS[chapterTwoWordIndex]}
          </span>
        </div>
      </section>

      <section
        ref={(el) => {
          chapterRefs.current[2] = el;
        }}
        data-chapter-index="2"
        className={chapterClass(2, styles.chapterJeton)}
      >
        <div className={`${styles.jetonStage} ${chapterThreePausedClass}`}>
          <div
            className={`${styles.jetonResearchShell} ${isActOneFrame ? styles.jetonResearchShellActOne : ""} ${isActTwoFrame ? styles.jetonResearchShellActTwo : ""} ${isActThreeFrame ? styles.jetonResearchShellActThree : ""} ${isActFourFrame ? styles.jetonResearchShellActFour : ""}`}
          >
            {isActOneFrame ? (
              <>
                <div className={styles.actOneCopyWrap}>
                  <p key={`act-one-copy-${chapterThreeReplaySeed}`} className={styles.actOneNarrativeText}>
                    {ACT_ONE_SCAN_COPY}
                  </p>
                </div>

                <div className={styles.actOneImageWrap}>
                  <img
                    key={`${activeChapterThree.step}-${activeChapterThree.imageSrc}-${chapterThreeReplaySeed}`}
                    src={activeChapterThree.imageSrc}
                    alt={`${activeChapterThree.title} research screen`}
                    className={`${styles.jetonResearchScreen} ${styles.jetonResearchScreenActOne}`}
                  />
                </div>

                <p key={`act-one-daily-${chapterThreeReplaySeed}`} className={styles.actOneDailyScanText}>
                  Daily Market Scans
                </p>
              </>
            ) : isActTwoFrame ? (
              <>
                <div className={styles.actTwoImageWrap}>
                  <img
                    key={`${activeChapterThree.step}-${activeChapterThree.imageSrc}-${chapterThreeReplaySeed}`}
                    src={activeChapterThree.imageSrc}
                    alt="Act 2 comparison scene"
                    className={`${styles.jetonResearchScreen} ${styles.jetonResearchScreenActTwo}`}
                  />
                </div>

                <p key={`act-two-right-${chapterThreeReplaySeed}`} className={styles.actTwoResearchOnlyText}>
                  {ACT_TWO_RESEARCH_ONLY_COPY}
                </p>

                <div key={`act-two-coin-${chapterThreeReplaySeed}`} className={styles.actTwoCoinFlipWrap}>
                  <span className={styles.actTwoCoinFlipToken} aria-hidden="true" />
                  <span className={styles.actTwoCoinFlipResult}>{ACT_TWO_COIN_RESULT_COPY}</span>
                </div>

                <p key={`act-two-top-${chapterThreeReplaySeed}`} className={styles.actTwoBrokageText}>
                  {ACT_TWO_BROKAGE_COPY}
                </p>
              </>
            ) : isActThreeFrame ? (
              <>
                {/* Panel A — Recommendations */}
                <div key={`act3-reco-${chapterThreeReplaySeed}`} className={styles.actThreePanelReco}>
                  <p className={styles.actThreePanelHeading}>{ACT_THREE_RECOMMENDATIONS_COPY}</p>
                  <img src="/uploads/Act3Recommendations.png" alt="Recommendations board" className={styles.actThreePanelImg} />
                  <p className={styles.actThreePanelCaption}>{ACT_THREE_UNBIASED_COPY}</p>
                </div>
                {/* Panel B — Watchlist */}
                <div key={`act3-watch-${chapterThreeReplaySeed}`} className={styles.actThreePanelWatch}>
                  <p className={styles.actThreePanelHeading}>{ACT_THREE_WATCHLIST_COPY}</p>
                  <img src="/uploads/Act3Watchlist.png" alt="Watchlist board" className={styles.actThreePanelImg} />
                  <p className={styles.actThreePanelCaption}>{ACT_THREE_WATCHLIST_MAINTAIN_COPY}</p>
                </div>
              </>
            ) : isActFourFrame ? (
              <div key={`act4-portfolio-${chapterThreeReplaySeed}`} className={styles.actFourPanel}>
                <p className={styles.actThreePanelHeading}>{ACT_FOUR_PORTFOLIO_COPY}</p>
                <img src="/uploads/Act4Portfolio.png" alt="Portfolio what-if tool" className={styles.actThreePanelImg} />
                <p className={styles.actThreePanelCaption}>{ACT_FOUR_OVERLINE_COPY}</p>
              </div>
            ) : (
              <>
                <div className={styles.jetonResearchHeader}>
                  <p key={`act-${activeChapterThree.step}-${chapterThreeReplaySeed}`} className={styles.jetonActLabel}>
                    {activeChapterThree.actLabel}
                  </p>
                  <h3 key={`title-${activeChapterThree.step}-${chapterThreeReplaySeed}`}>{activeChapterThree.title}</h3>
                  <p key={`subtitle-${activeChapterThree.step}-${chapterThreeReplaySeed}`}>{activeChapterThree.subtitle}</p>
                  <small key={`detail-${activeChapterThree.step}-${chapterThreeReplaySeed}`}>{activeChapterThree.detail}</small>
                </div>

                <div className={styles.jetonResearchScreenWrap}>
                  <img
                    key={`${activeChapterThree.step}-${activeChapterThree.imageSrc}-${chapterThreeReplaySeed}`}
                    src={activeChapterThree.imageSrc}
                    alt={`${activeChapterThree.title} research screen`}
                    className={styles.jetonResearchScreen}
                  />
                </div>
              </>
            )}
          </div>

          <div className={styles.jetonControlRail}>
            <div className={styles.jetonStepDots} role="tablist" aria-label="Chapter 3 process acts and restart">
              {CHAPTER_THREE_FRAMES.map((frame, index) => {
                const active = index === activeChapterThreeIndex;
                const isPlayingActive = active && chapterThreeIsPlaying && !chapterThreeIsPaused;
                return (
                  <button
                    key={frame.step}
                    type="button"
                    className={`${styles.jetonStepDotGlass} ${active ? styles.jetonStepDotGlassActive : ""} ${isPlayingActive ? styles.jetonStepDotGlassPlaying : ""}`}
                    onClick={() => startChapterThreeSequence(index)}
                    aria-selected={active}
                    aria-label={`Act ${frame.step} ${frame.title}`}
                  >
                    <img src={frame.iconSrc} alt="" aria-hidden="true" className={styles.jetonControlIcon} />
                    <span className={styles.srOnly}>{`Act ${frame.step}`}</span>
                  </button>
                );
              })}

              <button
                type="button"
                className={styles.jetonRestartDotGlass}
                onClick={() => startChapterThreeSequence(0)}
                aria-label="Restart chapter 3 sequence"
              >
                <img src="/uploads/ResetClearGlass.png" alt="" aria-hidden="true" className={styles.jetonControlIcon} />
                <span className={styles.srOnly}>Restart chapter 3 sequence</span>
              </button>

              <button
                type="button"
                className={`${styles.jetonPauseButton} ${chapterThreeIsPaused ? styles.jetonPauseButtonActive : ""}`}
                onClick={toggleChapterThreePause}
                disabled={chapterThreePauseDisabled}
                aria-label={chapterThreeIsPaused ? "Resume chapter 3 sequence" : "Pause chapter 3 sequence"}
              >
                {chapterThreeIsPaused ? "Resume" : "Pause"}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section
        ref={(el) => {
          chapterRefs.current[3] = el;
        }}
        data-chapter-index="3"
        className={chapterClass(3, styles.chapterFooterLead)}
      >
        <div className={styles.chapterFourVideoLayer} aria-hidden="true">
          <video
            key={`chapter-four-video-${chapterFourReplaySeed}`}
            ref={chapterFourVideoRef}
            className={styles.chapterFourVideo}
            autoPlay
            muted
            playsInline
            preload="auto"
          >
            <source src={CHAPTER_FOUR_VIDEO_SRC} type="video/mp4" />
          </video>
        </div>

        <p key={`chapter-four-neon-copy-${chapterFourReplaySeed}`} className={`${styles.chapterFourNeonCopy} ${neonTech.className}`}>
          {CHAPTER_FOUR_NEON_COPY}
        </p>

        <div className={styles.footerPanelFlat}>
          <div className={styles.footerInner}>
            {FOOTER_LINK_GROUPS.map((group) => (
              <section key={group.title} className={styles.footerGroup}>
                <h3>{group.title}</h3>
                <div className={styles.footerLinks}>
                  {group.links.map((link) => (
                    <Link key={`${group.title}-${link.label}`} href={link.href}>
                      {link.label}
                    </Link>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
