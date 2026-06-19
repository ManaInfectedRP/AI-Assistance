import { useEffect, useState } from 'react'

export interface KnowledgeProject {
  id: string
  name: string
  doc_count: number
}

export function useKnowledge() {
  const [projects, setProjects] = useState<KnowledgeProject[]>([])

  useEffect(() => {
    fetch('/api/knowledge/projects')
      .then((r) => r.json() as Promise<KnowledgeProject[]>)
      .then(setProjects)
      .catch(() => setProjects([]))
  }, [])

  return projects
}
