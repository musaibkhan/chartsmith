import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ChartSmith — forecast Helm upgrades",
  description: "Find every breaking change before you upgrade a Helm chart.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        />
        <style>{`
          * { box-sizing: border-box; }
          html, body { margin: 0; padding: 0; background: #0E1116; color: #E6E8EC;
            font-family: "Inter", ui-sans-serif, system-ui; }
          button { font-family: inherit; }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  );
}
