"use client";

import { useState } from "react";
import Image from "next/image";

interface ProviderLogoProps {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
}

export function ProviderLogo({ src, alt, className = "", width = 32, height = 32 }: ProviderLogoProps) {
  const [imageError, setImageError] = useState(false);

  if (imageError || !src) {
    return null;
  }

  return (
    <Image 
      src={src} 
      alt={alt}
      width={width}
      height={height}
      className={className}
      onError={() => setImageError(true)}
    />
  );
}
