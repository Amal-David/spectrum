"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ActivityIcon,
  AudioLinesIcon,
  LayoutDashboardIcon,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { callsRepository } from "@/lib/repositories/calls-repository"

const navigation = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboardIcon,
  },
  {
    title: "Calls",
    href: "/calls",
    icon: AudioLinesIcon,
  },
  {
    title: "Analysis",
    href: "/analysis",
    icon: ActivityIcon,
  },
]

export function AppSidebar() {
  const pathname = usePathname()
  const callCount = callsRepository.getAll().length

  return (
    <Sidebar variant="inset">
      <SidebarHeader>
        <div className="flex items-center justify-between gap-2 px-2 py-1">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium">Spectrum</span>
            <span className="text-xs text-muted-foreground">Voice agent analytics</span>
          </div>
          <Badge variant="secondary">Mock</Badge>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigation.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={pathname === item.href}
                  >
                    <item.icon />
                    <span className="truncate">{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Saved groups</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {callsRepository.getGroups().map((group) => (
                <SidebarMenuItem key={group.id}>
                  <SidebarMenuButton
                    render={<Link href={`/analysis?groupId=${group.id}`} />}
                    isActive={pathname === "/analysis"}
                  >
                    <span className="truncate">{group.name}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <Separator />
        <div className="flex items-center justify-between px-2 py-1 text-xs text-muted-foreground">
          <span>Total calls</span>
          <span className="font-mono tabular-nums">{callCount}</span>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
