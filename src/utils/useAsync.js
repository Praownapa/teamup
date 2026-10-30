import { useCallback, useEffect, useRef, useState } from 'react';

// Only the latest request may update state; ignore completions after unmount.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const generation = useRef(0);
  const run = useCallback(() => {
    const ticket = ++generation.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    return Promise.resolve().then(fn).then(
      (data) => { if (ticket === generation.current) setState({ data, loading: false, error: null }); },
      (error) => { if (ticket === generation.current) setState({ data: null, loading: false, error }); },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { run(); return () => { ++generation.current; }; }, [run]);
  return { ...state, reload: run };
}
