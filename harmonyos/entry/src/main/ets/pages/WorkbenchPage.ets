import { webview } from '@kit.ArkWeb';
import { isValidHttpUrl, normalizeBaseUrl } from '../common/UrlUtils';
import { Theme } from '../common/Theme';

@Component
export struct WorkbenchPage {
  @Prop @Watch('onWebBaseUrlChanged') webBaseUrl: string = '';
  @State currentUrl: string = '';
  @State loading: boolean = false;
  @State errorMessage: string = '';
  private controller: webview.WebviewController = new webview.WebviewController();

  aboutToAppear(): void {
    this.applyConfiguredUrl();
  }

  onWebBaseUrlChanged(): void {
    this.applyConfiguredUrl();
  }

  private applyConfiguredUrl(): void {
    const normalized: string = normalizeBaseUrl(this.webBaseUrl);
    if (!isValidHttpUrl(normalized)) {
      this.errorMessage = 'Web 工作台地址无效，请到“设置”中修改。';
      return;
    }
    this.errorMessage = '';
    this.currentUrl = normalized;
  }

  private reloadFromConfig(): void {
    const normalized: string = normalizeBaseUrl(this.webBaseUrl);
    if (!isValidHttpUrl(normalized)) {
      this.errorMessage = 'Web 工作台地址无效，请到“设置”中修改。';
      return;
    }
    this.errorMessage = '';
    this.currentUrl = normalized;
    try {
      this.controller.loadUrl(normalized);
    } catch (error) {
      this.errorMessage = '加载失败：' + (error instanceof Error ? error.message : 'Web 控制器尚未就绪');
    }
  }

  private refreshPage(): void {
    try {
      this.controller.refresh();
    } catch (error) {
      this.errorMessage = '刷新失败：' + (error instanceof Error ? error.message : 'Web 控制器尚未就绪');
    }
  }

  private goBack(): void {
    try {
      if (this.controller.accessBackward()) {
        this.controller.backward();
      }
    } catch (error) {
      this.errorMessage = '后退失败：' + (error instanceof Error ? error.message : 'Web 控制器尚未就绪');
    }
  }

  @Builder
  header() {
    Row() {
      Column({ space: 2 }) {
        Text('Web 工作台')
          .fontSize(25)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Text('ArkWeb 嵌入真实网页 · 非原生 AI')
          .fontSize(12)
          .fontColor(Theme.SEAL)
      }
      .alignItems(HorizontalAlign.Start)
      Blank()
      Text('WEB')
        .fontSize(11)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.WHITE)
        .padding({ left: 9, right: 9, top: 4, bottom: 4 })
        .backgroundColor(Theme.SEAL)
        .borderRadius(8)
    }
    .width('100%')
    .padding({ left: 20, right: 20, top: 18, bottom: 12 })
  }

  @Builder
  notice() {
    Column({ space: 5 }) {
      Text('这里嵌入的是电脑上的真实 Web 前端，不是原生 AI 工作台。')
        .fontSize(13)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.SEAL_DARK)
      Text('上传、修复、AI 推理与 3D 预览都发生在该网页及其后端 API 中。本页没有注入原生 JS 桥，也不会把网页操作伪装成原生能力。')
        .fontSize(11)
        .lineHeight(17)
        .fontColor(Theme.INK)
    }
    .width('100%')
    .padding(12)
    .backgroundColor('#392116')
    .borderRadius(12)
    .border({ width: 1, color: '#714424' })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  toolbar() {
    Column({ space: 8 }) {
      Row({ space: 8 }) {
        Button('后退')
          .type(ButtonType.Capsule)
          .height(30)
          .fontSize(11)
          .fontColor(Theme.INK)
          .backgroundColor(Theme.PAPER)
          .border({ width: 1, color: Theme.LINE })
          .onClick(() => {
            this.goBack();
          })
        Button('刷新')
          .type(ButtonType.Capsule)
          .height(30)
          .fontSize(11)
          .fontColor(Theme.INK)
          .backgroundColor(Theme.PAPER)
          .border({ width: 1, color: Theme.LINE })
          .onClick(() => {
            this.refreshPage();
          })
        Button('按设置重载')
          .type(ButtonType.Capsule)
          .height(30)
          .fontSize(11)
          .fontColor(Theme.WHITE)
          .backgroundColor(Theme.SEAL)
          .onClick(() => {
            this.reloadFromConfig();
          })
        Blank()
        if (this.loading) {
          LoadingProgress()
            .width(20)
            .height(20)
            .color(Theme.SEAL)
        }
      }
      .width('100%')

      Text(this.currentUrl.length > 0 ? this.currentUrl : '尚未配置 Web 地址')
        .fontSize(10)
        .fontColor(Theme.MUTED)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width('100%')
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 10, bottom: 8 })
    .backgroundColor(Theme.CARD)
    .borderRadius(14)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  invalidState() {
    Column({ space: 8 }) {
      Text('Web 地址不可用')
        .fontSize(17)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
      Text(this.errorMessage.length > 0 ? this.errorMessage : '请在设置页填写可访问的 http:// 或 https:// 地址。')
        .fontSize(12)
        .lineHeight(18)
        .fontColor(Theme.MUTED)
        .textAlign(TextAlign.Center)
    }
    .width('100%')
    .layoutWeight(1)
    .justifyContent(FlexAlign.Center)
    .padding(24)
  }

  @Builder
  securityFooter() {
    Row({ space: 12 }) {
      Text('仅 INTERNET')
        .fontSize(9)
        .fontColor(Theme.JADE)
      Text('无 JS Bridge')
        .fontSize(9)
        .fontColor(Theme.JADE)
      Text('文件访问关闭')
        .fontSize(9)
        .fontColor(Theme.JADE)
      Text('不绕过 SSL')
        .fontSize(9)
        .fontColor(Theme.JADE)
      Blank()
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 6, bottom: 8 })
  }

  build() {
    Column() {
      this.header()

      Column({ space: 10 }) {
        this.notice()
        this.toolbar()

        if (this.errorMessage.length > 0 && this.currentUrl.length > 0) {
          Text(this.errorMessage)
            .fontSize(10)
            .fontColor(Theme.DANGER)
            .width('100%')
            .padding(8)
            .backgroundColor('#442319')
            .borderRadius(8)
        }

        if (isValidHttpUrl(this.currentUrl)) {
          Web({ src: this.currentUrl, controller: this.controller })
            .width('100%')
            .layoutWeight(1)
            .javaScriptAccess(true)
            .domStorageAccess(true)
            .fileAccess(false)
            .geolocationAccess(false)
            .mixedMode(MixedMode.None)
            .onPageBegin(() => {
              this.loading = true;
              this.errorMessage = '';
            })
            .onPageEnd(() => {
              this.loading = false;
            })
            .onErrorReceive((event) => {
              if (event) {
                this.loading = false;
                this.errorMessage = 'Web 加载失败：' + event.error.getErrorInfo();
              }
            })
        } else {
          this.invalidState()
        }
      }
      .width('100%')
      .layoutWeight(1)
      .padding({ left: 12, right: 12 })
      .alignItems(HorizontalAlign.Start)

      this.securityFooter()
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.PAPER)
  }
}
