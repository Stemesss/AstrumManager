import { Router } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";

const router = Router();

const PYTHON_BOT_PORT = process.env["PYTHON_BOT_PORT"] ?? "6000";

router.use(
  "/telegram",
  createProxyMiddleware({
    target: `http://localhost:${PYTHON_BOT_PORT}`,
    changeOrigin: false,
    logger: console,
    on: {
      proxyReq: (proxyReq, req) => {
        const originalPath = (req as { originalUrl?: string }).originalUrl ?? req.url ?? "";
        proxyReq.path = originalPath;
      },
    },
  }),
);

export default router;
