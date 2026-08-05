"use client";

import { useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";

export type FlyoutRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const FLYOUT_MAX_WIDTH = 1160;
const FLYOUT_MAX_HEIGHT = 900;
const FLYOUT_MIN_WIDTH = 760;
const FLYOUT_MIN_HEIGHT = 460;
const FLYOUT_MARGIN_DESKTOP = 14;
const FLYOUT_MARGIN_MOBILE = 6;

type DragState = {
  pointerId: number;
  startX: number;
  startY: number;
  origin: FlyoutRect;
};

type ResizeState = {
  pointerId: number;
  startX: number;
  startY: number;
  origin: FlyoutRect;
};

function clampNumber(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function flyoutMargin(viewportWidth: number): number {
  return viewportWidth <= 920 ? FLYOUT_MARGIN_MOBILE : FLYOUT_MARGIN_DESKTOP;
}

function clampFlyoutRect(rect: FlyoutRect, viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  const maxWidth = Math.max(320, viewportWidth - margin * 2);
  const maxHeight = Math.max(260, viewportHeight - margin * 2);
  const minWidth = Math.min(FLYOUT_MIN_WIDTH, maxWidth);
  const minHeight = Math.min(FLYOUT_MIN_HEIGHT, maxHeight);
  const width = clampNumber(rect.width, minWidth, Math.min(FLYOUT_MAX_WIDTH, maxWidth));
  const height = clampNumber(rect.height, minHeight, Math.min(FLYOUT_MAX_HEIGHT, maxHeight));

  return {
    left: clampNumber(rect.left, margin, viewportWidth - margin - width),
    top: clampNumber(rect.top, margin, viewportHeight - margin - height),
    width,
    height,
  };
}

function defaultFlyoutRect(viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  const width = Math.min(FLYOUT_MAX_WIDTH, Math.max(Math.min(FLYOUT_MIN_WIDTH, viewportWidth - margin * 2), viewportWidth - margin * 2));
  const height = Math.min(FLYOUT_MAX_HEIGHT, Math.max(Math.min(FLYOUT_MIN_HEIGHT, viewportHeight - margin * 2), viewportHeight - margin * 2));

  return clampFlyoutRect(
    {
      left: Math.round((viewportWidth - width) / 2),
      top: Math.max(margin, Math.round((viewportHeight - height) / 2)),
      width,
      height,
    },
    viewportWidth,
    viewportHeight,
  );
}

function maximizedFlyoutRect(viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  return clampFlyoutRect(
    {
      left: margin,
      top: margin,
      width: viewportWidth - margin * 2,
      height: viewportHeight - margin * 2,
    },
    viewportWidth,
    viewportHeight,
  );
}

export function useFlyoutPanel(isOpen: boolean, onRequestClose?: () => void): {
  flyoutRect: FlyoutRect | null;
  flyoutMaximized: boolean;
  flyoutPanelStyle: CSSProperties | undefined;
  toggleFlyoutMaximize: () => void;
  onFlyoutHeaderPointerDown: (event: ReactPointerEvent<HTMLElement>) => void;
  onFlyoutHeaderPointerMove: (event: ReactPointerEvent<HTMLElement>) => void;
  onFlyoutHeaderPointerUp: (event: ReactPointerEvent<HTMLElement>) => void;
  onFlyoutHeaderPointerCancel: (event: ReactPointerEvent<HTMLElement>) => void;
  onFlyoutResizePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onFlyoutResizePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onFlyoutResizePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onFlyoutResizePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
} {
  const [flyoutRect, setFlyoutRect] = useState<FlyoutRect | null>(null);
  const [flyoutMaximized, setFlyoutMaximized] = useState(false);
  const flyoutRestoreRef = useRef<FlyoutRect | null>(null);
  const flyoutDragRef = useRef<DragState | null>(null);
  const flyoutResizeRef = useRef<ResizeState | null>(null);

  useEffect(() => {
    if (isOpen) return;
    flyoutRestoreRef.current = null;
    flyoutDragRef.current = null;
    flyoutResizeRef.current = null;
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const onResize = () => {
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      setFlyoutRect((current) => {
        if (flyoutMaximized) return maximizedFlyoutRect(viewportWidth, viewportHeight);
        const base = current ?? defaultFlyoutRect(viewportWidth, viewportHeight);
        return clampFlyoutRect(base, viewportWidth, viewportHeight);
      });
    };

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [isOpen, flyoutMaximized]);

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !onRequestClose) return;

    const handleKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onRequestClose();
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onRequestClose]);

  const effectiveFlyoutRect: FlyoutRect | null = (() => {
    if (!isOpen) return null;
    if (flyoutRect) return flyoutRect;
    if (typeof window === "undefined") return null;
    return defaultFlyoutRect(window.innerWidth, window.innerHeight);
  })();

  function toggleFlyoutMaximize(): void {
    if (!effectiveFlyoutRect) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (flyoutMaximized) {
      const restored = clampFlyoutRect(flyoutRestoreRef.current ?? defaultFlyoutRect(viewportWidth, viewportHeight), viewportWidth, viewportHeight);
      setFlyoutRect(restored);
      setFlyoutMaximized(false);
      flyoutRestoreRef.current = restored;
      return;
    }

    flyoutRestoreRef.current = effectiveFlyoutRect;
    setFlyoutRect(maximizedFlyoutRect(viewportWidth, viewportHeight));
    setFlyoutMaximized(true);
  }

  function onFlyoutHeaderPointerDown(event: ReactPointerEvent<HTMLElement>): void {
    if (flyoutMaximized || !effectiveFlyoutRect) return;
    if (event.button !== 0) return;

    const target = event.target as HTMLElement;
    if (target.closest('[data-flyout-control="true"]')) return;

    flyoutDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: effectiveFlyoutRect,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function onFlyoutHeaderPointerMove(event: ReactPointerEvent<HTMLElement>): void {
    const drag = flyoutDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    const next = {
      ...drag.origin,
      left: drag.origin.left + dx,
      top: drag.origin.top + dy,
    };
    const clamped = clampFlyoutRect(next, window.innerWidth, window.innerHeight);
    setFlyoutRect(clamped);
    flyoutRestoreRef.current = clamped;
  }

  function onFlyoutHeaderPointerUp(event: ReactPointerEvent<HTMLElement>): void {
    const drag = flyoutDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    flyoutDragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function onFlyoutHeaderPointerCancel(event: ReactPointerEvent<HTMLElement>): void {
    onFlyoutHeaderPointerUp(event);
  }

  function onFlyoutResizePointerDown(event: ReactPointerEvent<HTMLDivElement>): void {
    if (flyoutMaximized || !effectiveFlyoutRect) return;
    if (event.button !== 0) return;

    flyoutResizeRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: effectiveFlyoutRect,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
  }

  function onFlyoutResizePointerMove(event: ReactPointerEvent<HTMLDivElement>): void {
    const resize = flyoutResizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;

    const dx = event.clientX - resize.startX;
    const dy = event.clientY - resize.startY;
    const next = {
      ...resize.origin,
      width: resize.origin.width + dx,
      height: resize.origin.height + dy,
    };
    const clamped = clampFlyoutRect(next, window.innerWidth, window.innerHeight);
    setFlyoutRect(clamped);
    flyoutRestoreRef.current = clamped;
  }

  function onFlyoutResizePointerUp(event: ReactPointerEvent<HTMLDivElement>): void {
    const resize = flyoutResizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    flyoutResizeRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function onFlyoutResizePointerCancel(event: ReactPointerEvent<HTMLDivElement>): void {
    onFlyoutResizePointerUp(event);
  }

  const flyoutPanelStyle: CSSProperties | undefined = effectiveFlyoutRect
    ? {
        position: "fixed",
        left: effectiveFlyoutRect.left,
        top: effectiveFlyoutRect.top,
        width: effectiveFlyoutRect.width,
        height: effectiveFlyoutRect.height,
      }
    : undefined;

  return {
    flyoutRect: effectiveFlyoutRect,
    flyoutMaximized,
    flyoutPanelStyle,
    toggleFlyoutMaximize,
    onFlyoutHeaderPointerDown,
    onFlyoutHeaderPointerMove,
    onFlyoutHeaderPointerUp,
    onFlyoutHeaderPointerCancel,
    onFlyoutResizePointerDown,
    onFlyoutResizePointerMove,
    onFlyoutResizePointerUp,
    onFlyoutResizePointerCancel,
  };
}
