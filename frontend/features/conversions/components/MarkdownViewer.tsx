"use client";

import Markdown, { type Components } from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { outputUrl } from "@/lib/apiClient";

interface MarkdownViewerProps {
  /** نص الماركداون الخام */
  source: string;
  /** معرّف التحويل — يُستخدم لحل مسارات الصور النسبية */
  conversionId: string;
}

/** عناصر مصيّرة بتوكنز shadcn/Tailwind (تدعم الثيم الفاتح/الداكن تلقائيًا). */
const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="scroll-m-20 border-b border-border pb-2 text-2xl font-bold tracking-tight first:mt-0 mt-8">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="scroll-m-20 border-b border-border pb-2 text-xl font-semibold tracking-tight first:mt-0 mt-8">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="scroll-m-20 text-lg font-semibold tracking-tight mt-6">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="scroll-m-20 text-base font-semibold tracking-tight mt-6">{children}</h4>
  ),
  p: ({ children }) => <p className="leading-7 [&:not(:first-child)]:mt-4">{children}</p>,
  ul: ({ children }) => <ul className="ms-6 mt-4 list-disc space-y-2">{children}</ul>,
  ol: ({ children }) => <ol className="ms-6 mt-4 list-decimal space-y-2">{children}</ol>,
  li: ({ children }) => <li className="leading-7">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="mt-4 border-s-4 border-border ps-4 text-muted-foreground italic [&>p]:mt-0">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-primary underline underline-offset-4"
    >
      {children}
    </a>
  ),
  img: ({ src, alt }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt ?? ""}
      loading="lazy"
      className="mx-auto my-4 h-auto max-w-full rounded-lg border border-border shadow-sm"
    />
  ),
  table: ({ children }) => (
    <div className="mt-4 w-full overflow-x-auto rounded-lg border border-border">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-border px-3 py-2 text-start font-medium">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-border px-3 py-2 align-top">{children}</td>,
  tr: ({ children }) => <tr className="last:[&>td]:border-b-0">{children}</tr>,
  pre: ({ children }) => (
    <pre className="mt-4 overflow-x-auto rounded-lg border border-border bg-muted/60 p-4 font-mono text-sm leading-6 [&>code]:bg-transparent [&>code]:p-0">
      {children}
    </pre>
  ),
  code: ({ children }) => (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm font-medium">{children}</code>
  ),
  hr: () => <hr className="my-6 border-border" />,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  del: ({ children }) => <del className="text-muted-foreground">{children}</del>,
  input: (props) => <input {...props} disabled className="ms-1 me-2 accent-primary" />,
};

/**
 * عارض ماركداون خالص بهوية shadcn/Tailwind — لا يجلب بيانات بنفسه.
 * يعيد كتابة مسارات الصور النسبية (مفاتيح التخزين) إلى روابط تنزيل مطلقة.
 */
export function MarkdownViewer({ source, conversionId }: MarkdownViewerProps) {
  return (
    <article
      dir="rtl"
      className="overflow-auto rounded-lg border border-border bg-card px-5 py-6 text-card-foreground md:px-8"
    >
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={markdownComponents}
        urlTransform={(url) => {
          if (/^(https?:|data:|blob:|#)/i.test(url)) return url;
          const clean = url.replace(/^\.\//, "").replace(/^\/+/, "");
          const prefix = `${conversionId}/output/`;
          const key = clean.startsWith(prefix) ? clean.slice(prefix.length) : clean;
          return outputUrl(conversionId, key);
        }}
      >
        {source}
      </Markdown>
    </article>
  );
}
