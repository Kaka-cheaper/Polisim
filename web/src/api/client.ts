/**
 * REST API 客户端 —— axios wrapper（PR2）。
 *
 * 职责：
 *   1. 统一 baseURL（含 `/api/v1` 前缀）
 *   2. 把 server 的 `ErrorResponse` body（{ error: { code, message, detail? } }）
 *      解析为 `ApiError` 抛出 —— hooks 层 catch 时就能直接拿 status / code / message
 *   3. 对网络错误 / 超时 / server crash 也包成 `ApiError`，统一类型契约
 *
 * 不做的事（保持纯数据层）：
 *   - 不直接调 `toast.error()`——UI 层职责（hooks 各自的 onError）
 *   - 不做重试 / 断路器（react-query 自带）
 *   - 不做请求队列 / 节流（业务上不需要）
 *
 * **环境变量**：
 *   - `VITE_API_BASE`（可选，默认 `http://localhost:8000`）
 *   - `VITE_API_PREFIX`（可选，默认 `/api/v1`）—— 与 server `app.py:openapi_url` 对齐
 */
import axios, { type AxiosError } from "axios";

const DEFAULT_API_BASE = "http://localhost:8000";
const DEFAULT_API_PREFIX = "/api/v1";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, "") ??
  DEFAULT_API_BASE;
export const API_PREFIX: string =
  (import.meta.env.VITE_API_PREFIX as string | undefined) ?? DEFAULT_API_PREFIX;

/**
 * server 端 `ErrorBody` 的形状（对齐 `server/api/v1/errors.py:ErrorBody`）。
 *
 * 手动维护——`ErrorBody` 在 server 端没作 endpoint response_model 出现，
 * openapi-typescript 不会生成对应类型。
 */
export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}

/**
 * 业务统一错误 —— hooks / 组件层 catch 时拿到的形态。
 *
 * `status === 0` 表示网络层错误（无 HTTP 响应）；其他为 server 实际状态码。
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly detail?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.detail = body.detail;
  }

  /** 4xx 客户端错误（含 0 网络层错误归为客户端可重试范畴）。*/
  isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /** 5xx 服务器错误（不可控；通常需要 modal 提示用户）。*/
  isServerError(): boolean {
    return this.status >= 500;
  }
}

/**
 * 共享 axios 实例 —— hooks 通过它发请求。
 *
 * **不要**直接 export 让外层 import；hooks 应通过本文件提供的 `apiGet` / `apiPost` /
 * `apiDelete` helper（统一签名 + 类型推导友好）。
 */
const axiosInstance = axios.create({
  baseURL: `${API_BASE}${API_PREFIX}`,
  timeout: 60_000, // 60s——LLM provider 可能慢
  headers: { "Content-Type": "application/json" },
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as
      | { error?: ApiErrorBody }
      | ApiErrorBody
      | undefined;

    // server 端 errors.py 用 ErrorResponse(error=ErrorBody) 包装
    let body: ApiErrorBody | undefined;
    if (data && typeof data === "object" && "error" in data && data.error) {
      body = data.error;
    } else if (
      data &&
      typeof data === "object" &&
      "code" in data &&
      "message" in data
    ) {
      body = data as ApiErrorBody;
    }

    if (body) {
      return Promise.reject(new ApiError(status, body));
    }

    // 网络错误 / 超时 / 解析失败
    const code = error.code ?? "NETWORK_ERROR";
    const message =
      status === 0 ? "无法连接到服务器" : error.message || "请求失败";
    return Promise.reject(new ApiError(status, { code, message }));
  },
);

// === 业务 helper（hooks 层调用）===

export async function apiGet<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await axiosInstance.get<T>(path, { params });
  return response.data;
}

export async function apiPost<T, B = unknown>(
  path: string,
  body?: B,
): Promise<T> {
  const response = await axiosInstance.post<T>(path, body);
  return response.data;
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  const response = await axiosInstance.delete<T>(path);
  return response.data;
}
