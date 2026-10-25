import { common } from '@kit.AbilityKit';
import { AppSettings, SettingsRepository } from '../service/SettingsRepository';
import { HomePage } from './HomePage';
import { WorkbenchPage } from './WorkbenchPage';
import { SettingsPage } from './SettingsPage';
import { Theme } from '../common/Theme';

@Entry
@Component
struct Index {
  @State apiBaseUrl: string = 'http://127.0.0.1:8000';
  @State webBaseUrl: string = 'http://127.0.0.1:5173';
  @State selectedIndex: number = 0;
  @State refreshToken: number = 0;
  @State configReady: boolean = false;
  @State configError: string = '';

  async aboutToAppear(): Promise<void> {
    try {
      const context: common.UIAbilityContext = getContext(this) as common.UIAbilityContext;
      const settings: AppSettings = await SettingsRepository.getInstance().init(context);
      this.apiBaseUrl = settings.apiBaseUrl;
      this.webBaseUrl = settings.webBaseUrl;
    } catch (error) {
      this.configError = '读取本机 Preferences 失败，暂用回环默认值：' +
        (error instanceof Error ? error.message : '未知错误');
    } finally {
      this.configReady = true;
    }
  }

  private handleSettingsSaved(apiBaseUrl: string, webBaseUrl: string): void {
    this.apiBaseUrl = apiBaseUrl;
    this.webBaseUrl = webBaseUrl;
    this.refreshToken += 1;
  }

  @Builder
  splash() {
    Column({ space: 14 }) {
      Text('印')
        .fontSize(54)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.SEAL)
        .width(92)
        .height(92)
        .textAlign(TextAlign.Center)
        .border({ width: 3, color: Theme.SEAL })
        .borderRadius(14)
      LoadingProgress()
        .width(28)
        .height(28)
        .color(Theme.SEAL)
      Text('正在读取本机设置…')
        .fontSize(12)
        .fontColor(Theme.MUTED)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }

  @Builder
  tabItem(label: string, glyph: string, index: number) {
    Column({ space: 2 }) {
      Text(glyph)
        .fontSize(15)
        .fontWeight(FontWeight.Bold)
        .fontColor(this.selectedIndex === index ? Theme.WHITE : Theme.MUTED)
        .width(28)
        .height(23)
        .textAlign(TextAlign.Center)
        .backgroundColor(this.selectedIndex === index ? Theme.SEAL : Color.Transparent)
        .borderRadius(7)
      Text(label)
        .fontSize(10)
        .fontColor(this.selectedIndex === index ? Theme.SEAL : Theme.MUTED)
    }
    .width('100%')
    .height(54)
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Column() {
      if (!this.configReady) {
        this.splash()
      } else {
        if (this.configError.length > 0) {
          Text(this.configError)
            .fontSize(10)
            .fontColor(Theme.DANGER)
            .width('100%')
            .padding({ left: 14, right: 14, top: 8, bottom: 8 })
            .backgroundColor('#442319')
        }

        Tabs({ barPosition: BarPosition.End, index: this.selectedIndex }) {
          TabContent() {
            HomePage({
              apiBaseUrl: this.apiBaseUrl,
              refreshToken: this.refreshToken
            })
          }
          .tabBar(this.tabItem('首页', '印', 0))

          TabContent() {
            WorkbenchPage({
              webBaseUrl: this.webBaseUrl
            })
          }
          .tabBar(this.tabItem('工作台', '工', 1))

          TabContent() {
            SettingsPage({
              apiBaseUrl: this.apiBaseUrl,
              webBaseUrl: this.webBaseUrl,
              onSaved: (api: string, web: string) => {
                this.handleSettingsSaved(api, web);
              }
            })
          }
          .tabBar(this.tabItem('设置', '设', 2))
        }
        .barHeight(64)
        .barMode(BarMode.Fixed)
        .barBackgroundColor(Theme.CARD)
        .scrollable(false)
        .animationDuration(180)
        .width('100%')
        .height('100%')
        .onChange((index: number) => {
          this.selectedIndex = index;
        })
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.PAPER)
  }
}
