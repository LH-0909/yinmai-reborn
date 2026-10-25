import { common } from '@kit.AbilityKit';
import {
  DEFAULT_API_BASE_URL,
  DEFAULT_WEB_BASE_URL,
  SettingsRepository
} from '../service/SettingsRepository';
import { isValidHttpUrl, normalizeBaseUrl } from '../common/UrlUtils';
import { Theme } from '../common/Theme';

@Component
export struct SettingsPage {
  @Prop @Watch('syncFromProps') apiBaseUrl: string = '';
  @Prop @Watch('syncFromProps') webBaseUrl: string = '';
  onSaved: (apiBaseUrl: string, webBaseUrl: string) => void = () => {
  };
  @State draftApiBaseUrl: string = DEFAULT_API_BASE_URL;
  @State draftWebBaseUrl: string = DEFAULT_WEB_BASE_URL;
  @State saving: boolean = false;
  @State successMessage: string = '';
  @State errorMessage: string = '';

  aboutToAppear(): void {
    this.syncFromProps();
    this.loadPersistedSettings();
  }

  private syncFromProps(): void {
    if (this.apiBaseUrl.length > 0) {
      this.draftApiBaseUrl = this.apiBaseUrl;
    }
    if (this.webBaseUrl.length > 0) {
      this.draftWebBaseUrl = this.webBaseUrl;
    }
  }

  private async loadPersistedSettings(): Promise<void> {
    try {
      const context: common.UIAbilityContext = getContext(this) as common.UIAbilityContext;
      const settings = await SettingsRepository.getInstance().init(context);
      this.draftApiBaseUrl = settings.apiBaseUrl;
      this.draftWebBaseUrl = settings.webBaseUrl;
    } catch (error) {
      this.errorMessage = '读取本机 Preferences 失败：' +
        (error instanceof Error ? error.message : '未知错误');
    }
  }

  private async saveSettings(): Promise<void> {
    if (this.saving) {
      return;
    }
    const api: string = normalizeBaseUrl(this.draftApiBaseUrl);
    const web: string = normalizeBaseUrl(this.draftWebBaseUrl);
    this.errorMessage = '';
    this.successMessage = '';

    if (!isValidHttpUrl(api)) {
      this.errorMessage = 'API 地址无效。请填写类似 http://192.168.1.23:8000 的地址，且不要包含用户名或密码。';
      return;
    }
    if (!isValidHttpUrl(web)) {
      this.errorMessage = 'Web 工作台地址无效。请填写类似 http://192.168.1.23:5173 的地址，且不要包含用户名或密码。';
      return;
    }

    this.saving = true;
    try {
      const context: common.UIAbilityContext = getContext(this) as common.UIAbilityContext;
      await SettingsRepository.getInstance().init(context);
      const saved = await SettingsRepository.getInstance().save(api, web);
      this.draftApiBaseUrl = saved.apiBaseUrl;
      this.draftWebBaseUrl = saved.webBaseUrl;
      this.successMessage = '已写入本机 Preferences。原生页将使用新 API，工作台将加载新 Web 地址。';
      this.onSaved(saved.apiBaseUrl, saved.webBaseUrl);
    } catch (error) {
      this.errorMessage = '保存失败：' + (error instanceof Error ? error.message : '未知错误');
    } finally {
      this.saving = false;
    }
  }

  @Builder
  header() {
    Column({ space: 3 }) {
      Text('设置')
        .fontSize(25)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
      Text('设备上的 localhost ≠ 电脑的 localhost')
        .fontSize(12)
        .fontColor(Theme.SEAL)
    }
    .width('100%')
    .padding({ left: 20, right: 20, top: 18, bottom: 12 })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  fieldLabel(title: string, endpoint: string) {
    Row() {
      Text(title)
        .fontSize(13)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.INK)
      Blank()
      Text(endpoint)
        .fontSize(10)
        .fontColor(Theme.MUTED)
    }
    .width('100%')
  }

  @Builder
  addressCard() {
    Column({ space: 14 }) {
      Row() {
        Text('工作地址')
          .fontSize(17)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Blank()
        Text('本机持久化')
          .fontSize(10)
          .fontColor(Theme.JADE)
          .padding({ left: 8, right: 8, top: 3, bottom: 3 })
          .backgroundColor('#E6F0EA')
          .borderRadius(9)
      }
      .width('100%')

      Column({ space: 6 }) {
        this.fieldLabel('原生 API 根地址', 'GET /api/health')
        TextInput({ text: this.draftApiBaseUrl, placeholder: 'http://192.168.1.23:8000' })
          .height(48)
          .fontSize(14)
          .fontColor(Theme.INK)
          .placeholderColor('#A8998B')
          .caretColor(Theme.SEAL)
          .backgroundColor(Theme.PAPER)
          .borderRadius(10)
          .border({ width: 1, color: Theme.LINE })
          .padding({ left: 12, right: 12 })
          .onChange((value: string) => {
            this.draftApiBaseUrl = value;
            this.successMessage = '';
          })
        Text('用于原生健康检查、印谱列表、详情以及 original_url 图片。只填协议 + 主机 + 端口，不要附带账号密码。')
          .fontSize(10)
          .lineHeight(16)
          .fontColor(Theme.MUTED)
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)

      Column({ space: 6 }) {
        this.fieldLabel('ArkWeb 工作台地址', '真实 Web 前端')
        TextInput({ text: this.draftWebBaseUrl, placeholder: 'http://192.168.1.23:5173' })
          .height(48)
          .fontSize(14)
          .fontColor(Theme.INK)
          .placeholderColor('#A8998B')
          .caretColor(Theme.SEAL)
          .backgroundColor(Theme.PAPER)
          .borderRadius(10)
          .border({ width: 1, color: Theme.LINE })
          .padding({ left: 12, right: 12 })
          .onChange((value: string) => {
            this.draftWebBaseUrl = value;
            this.successMessage = '';
          })
        Text('仅用于“Web 工作台”页的 Web 组件，不会被注入原生 JS 桥。')
          .fontSize(10)
          .lineHeight(16)
          .fontColor(Theme.MUTED)
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)

      if (this.errorMessage.length > 0) {
        Text(this.errorMessage)
          .fontSize(11)
          .lineHeight(17)
          .fontColor(Theme.DANGER)
          .width('100%')
          .padding(10)
          .backgroundColor('#442319')
          .borderRadius(9)
      }

      if (this.successMessage.length > 0) {
        Text(this.successMessage)
          .fontSize(11)
          .lineHeight(17)
          .fontColor(Theme.JADE)
          .width('100%')
          .padding(10)
          .backgroundColor('#E6F0EA')
          .borderRadius(9)
      }

      Button(this.saving ? '正在写入…' : '保存设置')
        .width('100%')
        .height(46)
        .fontSize(15)
        .fontColor(Theme.WHITE)
        .backgroundColor(Theme.SEAL)
        .borderRadius(12)
        .enabled(!this.saving)
        .onClick(() => {
          this.saveSettings();
        })

      Text('只有保存成功后才会显示上面的成功提示；保存失败不会假装已连接。')
        .fontSize(10)
        .fontColor(Theme.MUTED)
        .width('100%')
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  networkGuide() {
    Column({ space: 10 }) {
      Text('怎么找到可用的局域网地址')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
      Text('1. 电脑与手机连接到同一个 Wi-Fi。')
        .fontSize(12)
        .lineHeight(19)
        .fontColor(Theme.INK)
      Text('2. Windows 执行 ipconfig，找到当前网卡的 IPv4 地址；例如 192.168.1.23。')
        .fontSize(12)
        .lineHeight(19)
        .fontColor(Theme.INK)
      Text('3. 替换成 http://<电脑IPv4>:8000 与 http://<电脑IPv4>:5173，保存后回到首页刷新。')
        .fontSize(12)
        .lineHeight(19)
        .fontColor(Theme.INK)
      Text('4. 后端和 Vite 都要监听 0.0.0.0，并允许 Windows 防火墙访问 8000 / 5173。')
        .fontSize(12)
        .lineHeight(19)
        .fontColor(Theme.INK)
      Text('不要在真机设置里填 127.0.0.1：那指向手机自身，不是电脑。默认值仅作为本机回环示例。部分模拟器可能可用 10.0.2.2 映射电脑。')
        .fontSize(11)
        .lineHeight(18)
        .fontColor(Theme.WARN)
        .width('100%')
        .padding(10)
        .backgroundColor('#FFF3DD')
        .borderRadius(9)
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  securityCard() {
    Column({ space: 8 }) {
      Text('安全边界')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
      Text('• 权限仅声明 ohos.permission.INTERNET。')
        .fontSize(11)
        .lineHeight(18)
        .fontColor(Theme.MUTED)
      Text('• ArkWeb 未注册 JavaScript Proxy / 任意原生桥，文件访问与定位关闭。')
        .fontSize(11)
        .lineHeight(18)
        .fontColor(Theme.MUTED)
      Text('• 未覆盖 SSL 错误回调，不信任无效证书；HTTPS 仍按系统校验。')
        .fontSize(11)
        .lineHeight(18)
        .fontColor(Theme.MUTED)
      Text('• 为连接本地 HTTP 后端，应用包内声明了开发期明文流量配置；生产部署应改为 HTTPS 并收紧该配置。')
        .fontSize(11)
        .lineHeight(18)
        .fontColor(Theme.WARN)
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  aboutCard() {
    Column({ space: 5 }) {
      Text('印脉重生 · HarmonyOS NEXT Starter')
        .fontSize(13)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.INK)
      Text('版本 0.1.0 · Stage 模型 · ArkTS / ArkUI / ArkWeb')
        .fontSize(10)
        .fontColor(Theme.MUTED)
      Text('未包含签名证书或凭据。是否编译、签名、真机可运行，以实际 DevEco 构建结果为准。')
        .fontSize(10)
        .lineHeight(16)
        .fontColor(Theme.MUTED)
    }
    .width('100%')
    .padding(14)
    .backgroundColor(Theme.PAPER_DEEP)
    .borderRadius(12)
    .alignItems(HorizontalAlign.Start)
  }

  build() {
    Column() {
      this.header()
      Scroll() {
        Column({ space: 14 }) {
          this.addressCard()
          this.networkGuide()
          this.securityCard()
          this.aboutCard()
        }
        .width('100%')
        .padding({ left: 16, right: 16, bottom: 24 })
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.PAPER)
  }
}
