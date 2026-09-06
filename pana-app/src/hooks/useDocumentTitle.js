import { useEffect } from 'react';

/** Shown alone on screens with no page of their own, and as the suffix elsewhere. */
const APP_NAME = 'Pana';

/**
 * Set the browser tab's title for as long as a component is mounted.
 *
 * The tab is the only place the app says where you are once it is one of
 * several windows open, so each screen names itself there. The app name comes
 * second: with a dozen tabs open the browser truncates from the right, and the
 * half worth keeping is the page, not the twelfth repetition of "Pana".
 *
 * @param {string} [title] The page's name. Omit for the app name alone.
 */
export function useDocumentTitle(title) {
  useEffect(() => {
    const previous = document.title;
    document.title = title ? `${title} — ${APP_NAME}` : APP_NAME;

    // Restoring on unmount keeps a slow route transition from leaving the old
    // page's name in the tab.
    return () => {
      document.title = previous;
    };
  }, [title]);
}

export default useDocumentTitle;
