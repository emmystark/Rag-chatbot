import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";  // Google Fonts: Pro AI choice
import "./globals.css";
import { ThemeProvider } from "next-themes";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  weight: ["400", "500", "700"],  // Light set for chat readability
  display: "swap",  // No layout shift
});

export const metadata: Metadata = {
  title: "Company Knowledge Bot",
  description: "Production-grade RAG chatbot with citations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${jetbrainsMono.variable} font-mono antialiased min-h-screen`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}