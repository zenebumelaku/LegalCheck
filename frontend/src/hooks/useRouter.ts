import { useState, useEffect, useCallback } from 'react';

export interface RouteMatch {
  path: string;
  params: Record<string, string>;
  query: Record<string, string>;
}

export function useRouter() {
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return window.location.pathname || '/';
    }
    return '/';
  });

  const [searchParams, setSearchParams] = useState<Record<string, string>>(() => {
    if (typeof window !== 'undefined') {
      const sp = new URLSearchParams(window.location.search);
      const res: Record<string, string> = {};
      sp.forEach((v, k) => {
        res[k] = v;
      });
      return res;
    }
    return {};
  });

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
      const sp = new URLSearchParams(window.location.search);
      const res: Record<string, string> = {};
      sp.forEach((v, k) => {
        res[k] = v;
      });
      setSearchParams(res);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = useCallback((path: string, query?: Record<string, string>) => {
    let target = path;
    if (query) {
      const sp = new URLSearchParams();
      Object.entries(query).forEach(([k, v]) => {
        if (v) sp.append(k, v);
      });
      const qs = sp.toString();
      if (qs) target += `?${qs}`;
    }

    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', target);
      setCurrentPath(path);
      const sp = new URLSearchParams(window.location.search);
      const res: Record<string, string> = {};
      sp.forEach((v, k) => {
        res[k] = v;
      });
      setSearchParams(res);
      window.scrollTo(0, 0);
    }
  }, []);

  return {
    path: currentPath,
    searchParams,
    navigate
  };
}
