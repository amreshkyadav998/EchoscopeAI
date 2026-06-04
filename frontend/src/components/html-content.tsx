"use client";

/**
 * Renders server-provided HTML (e.g. an alert/report preview) via
 * dangerouslySetInnerHTML. Only pass HTML from trusted backend sources — this
 * bypasses React's escaping, so never feed it raw user input.
 */
export function HtmlContent({ html, className }: { html: string; className?: string }) {
  return <div className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
