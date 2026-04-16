import { CallsView } from "@/components/app/calls-view"
import { callsRepository } from "@/lib/repositories/calls-repository"

export default function CallsPage() {
  return <CallsView calls={callsRepository.getAll()} />
}
