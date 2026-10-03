# Contract: the page in Telegram

1. The script is requested **only** when the URL hash carries `tgWebAppData`.
2. Inside Telegram: `ready()` and `expand()` once; `disableVerticalSwipes()` when present; theme applied
   as CSS variables and a colour scheme; the back button shown on a chart route, hidden on the overview,
   and a press navigates to `/`; every API request carries `Authorization: tma <initData>`.
3. Outside Telegram: no script request, no header, no call to anything Telegram, no throw.
4. A `start_param` replaces the address **before** the page reads it, only when it decodes to an allowed
   path; otherwise the overview.
5. The dev launch string exists only under `import.meta.env.DEV`.
