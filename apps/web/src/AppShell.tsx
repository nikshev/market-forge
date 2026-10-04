// @trace: REQ-WP-083
//
// The frame of every page: an app bar with the logo and the product's name, once, as the page's only level-one
// heading; the page in a main landmark; and, on a chart in a browser, a way back to the overview. Inside
// Telegram its own back button does that (REQ-WP-080), so none is drawn.

import ArrowBackIosNew from "@mui/icons-material/ArrowBackIosNew";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

import { webApp } from "./telegram";

export function AppShell({
  back,
  children,
}: {
  back?: string;
  children: ReactNode;
}): JSX.Element {
  const showBack = back !== undefined && webApp() === undefined;
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", color: "text.primary" }}>
      <AppBar
        position="sticky"
        color="inherit"
        elevation={0}
        sx={{ bgcolor: "background.paper", borderBottom: 1, borderColor: "divider" }}
      >
        <Toolbar variant="dense" sx={{ gap: 1 }}>
          {showBack ? (
            <IconButton
              component="a"
              href={back}
              edge="start"
              size="small"
              aria-label="Back to markets"
            >
              <ArrowBackIosNew fontSize="small" />
            </IconButton>
          ) : null}
          {/* Decorative: the name beside it is the name. */}
          <Box component="img" src="/logo.svg" alt="" sx={{ height: 28, width: 28 }} />
          <Typography variant="h6" component="h1" noWrap>
            Market Forge
          </Typography>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: 2 }}>
        {children}
      </Container>
    </Box>
  );
}
