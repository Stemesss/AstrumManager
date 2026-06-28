import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());

app.use((req, _res, next) => {
  if (req.path.startsWith("/api/telegram")) {
    return next();
  }
  express.json()(req, _res, () => {
    express.urlencoded({ extended: true })(req, _res, next);
  });
});

app.use("/api", router);

export default app;
