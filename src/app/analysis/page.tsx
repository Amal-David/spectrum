import { AnalysisWorkspace } from "@/components/app/analysis-workspace"
import { parseAnalysisScope } from "@/lib/analysis-scope"
import { analysisRepository } from "@/lib/repositories/analysis-repository"

type AnalysisPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function AnalysisPage({
  searchParams,
}: AnalysisPageProps) {
  const resolvedSearchParams = await searchParams
  const scope = parseAnalysisScope(resolvedSearchParams)
  const dataset = analysisRepository.getByScope(scope)

  return <AnalysisWorkspace dataset={dataset} />
}
