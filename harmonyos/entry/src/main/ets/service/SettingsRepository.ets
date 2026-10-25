import { preferences } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { isValidHttpUrl, normalizeBaseUrl } from '../common/UrlUtils';

export const DEFAULT_API_BASE_URL: string = 'http://127.0.0.1:8000';
export const DEFAULT_WEB_BASE_URL: string = 'http://127.0.0.1:5173';

const PREF_NAME: string = 'yinmai_reborn_settings';
const KEY_API_BASE_URL: string = 'apiBaseUrl';
const KEY_WEB_BASE_URL: string = 'webBaseUrl';

export class AppSettings {
  apiBaseUrl: string;
  webBaseUrl: string;

  constructor(apiBaseUrl: string, webBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl;
    this.webBaseUrl = webBaseUrl;
  }
}

export class SettingsRepository {
  private static readonly INSTANCE: SettingsRepository = new SettingsRepository();
  private store: preferences.Preferences | null = null;
  private initialized: boolean = false;
  private cached: AppSettings = new AppSettings(DEFAULT_API_BASE_URL, DEFAULT_WEB_BASE_URL);

  private constructor() {
  }

  static getInstance(): SettingsRepository {
    return SettingsRepository.INSTANCE;
  }

  async init(context: common.Context): Promise<AppSettings> {
    if (this.initialized && this.store !== null) {
      return this.cached;
    }
    const store: preferences.Preferences = await preferences.getPreferences(context, PREF_NAME);
    const apiValue: preferences.ValueType = await store.get(KEY_API_BASE_URL, DEFAULT_API_BASE_URL);
    const webValue: preferences.ValueType = await store.get(KEY_WEB_BASE_URL, DEFAULT_WEB_BASE_URL);
    const apiBaseUrl: string = typeof apiValue === 'string' ? apiValue : DEFAULT_API_BASE_URL;
    const webBaseUrl: string = typeof webValue === 'string' ? webValue : DEFAULT_WEB_BASE_URL;
    this.store = store;
    this.cached = new AppSettings(apiBaseUrl, webBaseUrl);
    this.initialized = true;
    return this.cached;
  }

  getCached(): AppSettings {
    return this.cached;
  }

  async save(apiBaseUrl: string, webBaseUrl: string): Promise<AppSettings> {
    const api: string = normalizeBaseUrl(apiBaseUrl);
    const web: string = normalizeBaseUrl(webBaseUrl);
    if (!isValidHttpUrl(api)) {
      throw new Error('API 地址必须是有效的 http:// 或 https:// 地址');
    }
    if (!isValidHttpUrl(web)) {
      throw new Error('Web 工作台地址必须是有效的 http:// 或 https:// 地址');
    }
    if (this.store === null) {
      throw new Error('本机设置尚未初始化，请重新进入页面后再试');
    }
    await this.store.put(KEY_API_BASE_URL, api);
    await this.store.put(KEY_WEB_BASE_URL, web);
    await this.store.flush();
    this.cached = new AppSettings(api, web);
    this.initialized = true;
    return this.cached;
  }
}
