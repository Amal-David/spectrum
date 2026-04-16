import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";

import { AppHeader } from "@/components/app/app-header";
import { AppSidebar } from "@/components/app/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Spectrum",
  description: "Shadcn-first analytics workspace for voice AI agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full overflow-x-hidden">
        <TooltipProvider>
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
              <Suspense fallback={<AppHeaderFallback />}>
                <AppHeader />
              </Suspense>
              <main className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
                {children}
              </main>
            </SidebarInset>
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}

function AppHeaderFallback() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-4">
      <div className="w-8" />
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-sm font-medium">Spectrum</span>
        <span className="text-sm text-muted-foreground">Dashboard</span>
      </div>
    </header>
  );
}
