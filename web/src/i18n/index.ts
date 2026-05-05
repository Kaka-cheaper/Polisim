/**
 * react-i18next 初始化 —— PR1 落地。
 *
 * 设计要点：
 *   1. **单一真理是 zustand uiStore.locale**——本文件初始化时不读 localStorage，
 *      避免与 ui_store 的 persist 中间件竞争。i18n 启动用 'zh' 默认；App.tsx 的
 *      useEffect 把 store.locale 同步到 i18n（`i18n.changeLanguage(locale)`）。
 *      zustand persist 是 sync hydrate，用户首屏看到的语言已是上次保存值。
 *   2. **资源静态 import**——zh.json / en.json 编译期内联，不增加运行时请求。
 *   3. **escapeValue: false**——React 已防 XSS，避免 i18next 双重转义。
 *   4. **fallbackLng: 'zh'**——与 mockup §5.3 一致（中文是项目主语言）。
 *
 * 入口：在 main.tsx 里 `import './i18n'` 即触发 init（必须在 App 渲染前）。
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import zh from "./zh.json";

void i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: "zh",
  fallbackLng: "zh",
  interpolation: { escapeValue: false },
});

export default i18n;
