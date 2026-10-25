import { http } from '@kit.NetworkKit';
import { HealthResponse, SealRecord } from '../model/Models';
import { isValidHttpUrl, joinApiPath } from '../common/UrlUtils';

export class ApiClient {
  private static async getText(baseUrl: string, path: string): Promise<string> {
    if (!isValidHttpUrl(baseUrl)) {
      throw new Error('API 地址无效，请先在“设置”中填写 http:// 或 https:// 地址');
    }
    const url: string = joinApiPath(baseUrl, path);
    const request: http.HttpRequest = http.createHttp();
    const options: http.HttpRequestOptions = {
      method: http.RequestMethod.GET,
      header: {
        'Accept': 'application/json'
      },
      connectTimeout: 10000,
      readTimeout: 15000,
      expectDataType: http.HttpDataType.STRING,
      usingCache: false
    };
    try {
      const response: http.HttpResponse = await request.request(url, options);
      if (response.responseCode < 200 || response.responseCode >= 300) {
        throw new Error('后端返回 HTTP ' + response.responseCode.toString());
      }
      const body: string | Object | ArrayBuffer = response.result;
      if (typeof body !== 'string') {
        throw new Error('后端响应不是文本 JSON');
      }
      return body;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error('请求 ' + url + ' 失败：' + error.message);
      }
      throw new Error('请求 ' + url + ' 失败');
    } finally {
      request.destroy();
    }
  }

  static async fetchHealth(apiBaseUrl: string): Promise<HealthResponse> {
    const body: string = await ApiClient.getText(apiBaseUrl, '/api/health');
    try {
      const parsed: HealthResponse = JSON.parse(body) as HealthResponse;
      if (parsed === null || parsed.database === undefined || parsed.counts === undefined) {
        throw new Error('缺少 database 或 counts 字段');
      }
      return parsed;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error('健康检查 JSON 格式错误：' + error.message);
      }
      throw new Error('健康检查 JSON 格式错误');
    }
  }

  static async fetchSeals(apiBaseUrl: string): Promise<SealRecord[]> {
    const body: string = await ApiClient.getText(apiBaseUrl, '/api/seals');
    try {
      const parsed: Object = JSON.parse(body);
      if (!Array.isArray(parsed)) {
        throw new Error('/api/seals 应返回数组');
      }
      return parsed as SealRecord[];
    } catch (error) {
      if (error instanceof Error) {
        throw new Error('印谱列表 JSON 格式错误：' + error.message);
      }
      throw new Error('印谱列表 JSON 格式错误');
    }
  }

  static async fetchSeal(apiBaseUrl: string, id: string): Promise<SealRecord> {
    if (id.length === 0) {
      throw new Error('印谱 ID 为空');
    }
    const body: string = await ApiClient.getText(apiBaseUrl, '/api/seals/' + id);
    try {
      const parsed: SealRecord = JSON.parse(body) as SealRecord;
      if (parsed === null || parsed.id === undefined) {
        throw new Error('/api/seals/{id} 应返回印谱对象');
      }
      return parsed;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error('印谱详情 JSON 格式错误：' + error.message);
      }
      throw new Error('印谱详情 JSON 格式错误');
    }
  }
}
