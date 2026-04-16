"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useSearchParams } from "next/navigation"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { getAppShellState } from "@/lib/navigation"

export function AppHeader() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const shellState = getAppShellState({
    pathname,
    searchParams: new URLSearchParams(searchParams.toString()),
  })

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <div className="min-w-0">
        <Breadcrumb className="min-w-0">
          <BreadcrumbList>
            {shellState.breadcrumbs.map((item, index) => {
              const isLastItem = index === shellState.breadcrumbs.length - 1

              return (
                <React.Fragment key={`${item.label}-${index}`}>
                  <BreadcrumbItem>
                    {item.href && !isLastItem ? (
                      <BreadcrumbLink render={<Link href={item.href} />}>
                        {item.label}
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage className="truncate">
                        {item.label}
                      </BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                  {!isLastItem ? (
                    <BreadcrumbSeparator className="text-muted-foreground" />
                  ) : null}
                </React.Fragment>
              )
            })}
          </BreadcrumbList>
        </Breadcrumb>
      </div>
    </header>
  )
}
