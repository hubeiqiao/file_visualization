"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name2 in all)
    __defProp(target, name2, { get: all[name2], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/generic.ts
var generic_exports = {};
__export(generic_exports, {
  computeRoute: () => computeRoute,
  default: () => generic_default,
  injectSpeedInsights: () => injectSpeedInsights
});
module.exports = __toCommonJS(generic_exports);

// package.json
var name = "@vercel/speed-insights";
var version = "1.2.0";

// src/queue.ts
var initQueue = () => {
  if (window.si) return;
  window.si = function a(...params) {
    (window.siq = window.siq || []).push(params);
  };
};

// src/utils.ts
function isBrowser() {
  return typeof window !== "undefined";
}
function detectEnvironment() {
  try {
    const env = process.env.NODE_ENV;
    if (env === "development" || env === "test") {
      return "development";
    }
  } catch (e) {
  }
  return "production";
}
function isDevelopment() {
  return detectEnvironment() === "development";
}
function computeRoute(pathname, pathParams) {
  if (!pathname || !pathParams) {
    return pathname;
  }
  let result = pathname;
  try {
    const entries = Object.entries(pathParams);
    for (const [key, value] of entries) {
      if (!Array.isArray(value)) {
        const matcher = turnValueToRegExp(value);
        if (matcher.test(result)) {
          result = result.replace(matcher, `/[${key}]`);
        }
      }
    }
    for (const [key, value] of entries) {
      if (Array.isArray(value)) {
        const matcher = turnValueToRegExp(value.join("/"));
        if (matcher.test(result)) {
          result = result.replace(matcher, `/[...${key}]`);
        }
      }
    }
    return result;
  } catch (e) {
    return pathname;
  }
}
function turnValueToRegExp(value) {
  return new RegExp(`/${escapeRegExp(value)}(?=[/?#]|$)`);
}
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function getScriptSrc(props) {
  if (props.scriptSrc) {
    return props.scriptSrc;
  }
  if (isDevelopment()) {
    return "https://va.vercel-scripts.com/v1/speed-insights/script.debug.js";
  }
  if (props.dsn) {
    return "https://va.vercel-scripts.com/v1/speed-insights/script.js";
  }
  if (props.basePath) {
    return `${props.basePath}/speed-insights/script.js`;
  }
  return "/_vercel/speed-insights/script.js";
}

// src/generic.ts
function injectSpeedInsights(props = {}) {
  var _a;
  if (!isBrowser() || props.route === null) return null;
  initQueue();
  const src = getScriptSrc(props);
  if (document.head.querySelector(`script[src*="${src}"]`)) return null;
  if (props.beforeSend) {
    (_a = window.si) == null ? void 0 : _a.call(window, "beforeSend", props.beforeSend);
  }
  const script = document.createElement("script");
  script.src = src;
  script.defer = true;
  script.dataset.sdkn = name + (props.framework ? `/${props.framework}` : "");
  script.dataset.sdkv = version;
  if (props.sampleRate) {
    script.dataset.sampleRate = props.sampleRate.toString();
  }
  if (props.route) {
    script.dataset.route = props.route;
  }
  if (props.endpoint) {
    script.dataset.endpoint = props.endpoint;
  } else if (props.basePath) {
    script.dataset.endpoint = `${props.basePath}/speed-insights/vitals`;
  }
  if (props.dsn) {
    script.dataset.dsn = props.dsn;
  }
  if (isDevelopment() && props.debug === false) {
    script.dataset.debug = "false";
  }
  script.onerror = () => {
    console.log(
      `[Vercel Speed Insights] Failed to load script from ${src}. Please check if any content blockers are enabled and try again.`
    );
  };
  document.head.appendChild(script);
  return {
    setRoute: (route) => {
      script.dataset.route = route ?? void 0;
    }
  };
}
var generic_default = {
  injectSpeedInsights,
  computeRoute
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  computeRoute,
  injectSpeedInsights
});
//# sourceMappingURL=index.js.map