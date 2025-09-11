"use client";

import { useState } from "react";

interface ProviderLogoProps {
  src: string;
  alt: string;
  className?: string;
}

export function ProviderLogo({ src, alt, className = "" }: ProviderLogoProps) {
  const [imageError, setImageError] = useState(false);

  if (imageError || !src) {
    return null;
  }

  return (
    <img 
      src={src} 
      alt={alt}
      className={className}
      onError={() => setImageError(true)}
    />
  );
}
