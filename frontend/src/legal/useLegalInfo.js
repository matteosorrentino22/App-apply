import { useEffect, useState } from 'react'
import { fetchLegalInfo } from '../api/legal'

export function useLegalInfo() {
  const [info, setInfo] = useState(null)
  useEffect(() => {
    let active = true
    fetchLegalInfo()
      .then((data) => active && setInfo(data))
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])
  return info
}
