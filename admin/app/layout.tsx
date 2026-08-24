import type { Metadata } from "next";
import { Inter, Newsreader } from "next/font/google";

import "./styles.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const editorial = Newsreader({ subsets: ["latin"], variable: "--font-editorial" });

export const metadata: Metadata = {
  title: "Yard Moderation",
  description: "Private moderation operations for Yard.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${editorial.variable}`}>{children}</body>
    </html>
  );
}
