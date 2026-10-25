import { router } from '@kit.ArkUI';
import { ApiClient } from '../service/ApiClient';
import { DetailRouteParams, HealthResponse, SealRecord } from '../model/Models';
import { SealCard } from '../components/SealCard';
import { formatClock } from '../common/Format';
import { Theme } from '../common/Theme';

@Component
export struct HomePage {
  @Prop apiBaseUrl: string = '';
  @Prop @Watch('onRefreshRequested') refreshToken: number = 0;
  @State health: HealthResponse | null = null;
  @State seals: SealRecord[] = [];
  @State loading: boolean = false;
  @State errorMessage: string = '';
  @State lastLoadedAt: string = '';
  private requestSeq: number = 0;

  aboutToAppear(): void {
    this.loadData();
  }

  onRefreshRequested(): void {
    this.loadData();
  }

  private async loadData(): Promise<void> {
    this.requestSeq += 1;
    const seq: number = this.requestSeq;
    this.loading = true;
    this.errorMessage = '';
    try {
      const health: HealthResponse = await ApiClient.fetchHealth(this.apiBaseUrl);
      const seals: SealRecord[] = await ApiClient.fetchSeals(this.apiBaseUrl);
      if (seq !== this.requestSeq) {
        return;
      }
      this.health = health;
      this.seals = seals;
      this.lastLoadedAt = formatClock(new Date());
    } catch (error) {
      if (seq !== this.requestSeq) {
        return;
      }
      this.health = null;
      this.seals = [];
      this.errorMessage = error instanceof Error ? error.message : '未知请求错误';
    } finally {
      if (seq === this.requestSeq) {
        this.loading = false;
      }
    }
  }

  private hostLabel(): string {
    const index: number = this.apiBaseUrl.indexOf('://');
    return index >= 0 ? this.apiBaseUrl.substring(index + 3) : this.apiBaseUrl;
  }

  private aiSummary(health: HealthResponse): string {
    try {
      const text: string = JSON.stringify(health.ai);
      return text.length > 0 ? text : '{}';
    } catch (error) {
      return 'AI 状态字段无法序列化';
    }
  }

  private databaseColor(health: HealthResponse): string {
    return health.database === 'connected' ? Theme.JADE : Theme.WARN;
  }

  private databaseText(health: HealthResponse): string {
    if (health.database === 'connected') {
      return '数据库已连接';
    }
    return '数据库状态：' + (health.database.length > 0 ? health.database : '未返回');
  }

  private databaseEngine(health: HealthResponse): string {
    const engine: string = health.database_engine;
    return engine !== undefined && engine.length > 0 ? engine : '数据库引擎未返回';
  }

  private openDetail(id: string): void {
    router.pushUrl({
      url: 'pages/SealDetail',
      params: new DetailRouteParams(id, this.apiBaseUrl)
    });
  }

  @Builder
  header() {
    Row() {
      Column({ space: 2 }) {
        Text('印脉重生')
          .fontSize(25)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Text('NATIVE · 端侧原生入口')
          .fontSize(10)
          .letterSpacing(1.2)
          .fontColor(Theme.SEAL)
      }
      .alignItems(HorizontalAlign.Start)

      Blank()

      Column({ space: 2 }) {
        Text('API')
          .fontSize(10)
          .fontColor(Theme.MUTED)
        Text(this.hostLabel())
          .fontSize(11)
          .fontColor(Theme.INK)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .constraintSize({ maxWidth: 150 })
      }
      .alignItems(HorizontalAlign.End)
    }
    .width('100%')
    .padding({ left: 20, right: 20, top: 18, bottom: 12 })
  }

  @Builder
  hero() {
    Row() {
      Column({ space: 8 }) {
        Text('端 · 云 · 智')
          .fontSize(11)
          .letterSpacing(2)
          .fontColor('#E7C6B7')
        Text('让真实印谱在鸿蒙上被看见')
          .fontSize(23)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.WHITE)
          .maxLines(2)
        Text('原生页只读取真实后端。上传、图像修复、AI 推理与 3D 仍由 Web 工作台完成。')
          .fontSize(12)
          .lineHeight(19)
          .fontColor('#DCCFC2')
          .maxLines(3)
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)

      Text('印')
        .fontSize(64)
        .fontWeight(FontWeight.Bold)
        .fontColor('#C96A5D')
        .width(76)
        .height(76)
        .textAlign(TextAlign.Center)
        .border({ width: 2, color: '#B85A4E' })
        .borderRadius(12)
    }
    .width('100%')
    .padding(20)
    .backgroundColor(Theme.INK)
    .borderRadius(22)
  }

  @Builder
  metric(label: string, value: number) {
    Column({ space: 3 }) {
      Text(value.toString())
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
      Text(label)
        .fontSize(11)
        .fontColor(Theme.MUTED)
    }
    .layoutWeight(1)
    .padding(12)
    .backgroundColor(Theme.PAPER)
    .borderRadius(12)
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  healthContent(health: HealthResponse) {
    Column({ space: 12 }) {
      Row({ space: 8 }) {
        Text('●')
          .fontSize(12)
          .fontColor(this.databaseColor(health))
        Text(this.databaseText(health))
          .fontSize(14)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.INK)
        Blank()
        Text(this.databaseEngine(health))
          .fontSize(11)
          .fontColor(Theme.MUTED)
      }
      .width('100%')

      Row({ space: 10 }) {
        this.metric('印谱 seals', health.counts.seals)
        this.metric('产物 artifacts', health.counts.artifacts)
      }
      .width('100%')

      Column({ space: 4 }) {
        Text('AI 状态（后端返回原样）')
          .fontSize(11)
          .fontColor(Theme.MUTED)
        Text(this.aiSummary(health))
          .fontSize(11)
          .fontColor(Theme.INK)
          .maxLines(5)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')
      }
      .width('100%')
      .padding(10)
      .backgroundColor(Theme.PAPER)
      .borderRadius(10)
      .alignItems(HorizontalAlign.Start)

      if (this.lastLoadedAt.length > 0) {
        Text('本机读取时间 ' + this.lastLoadedAt)
          .fontSize(10)
          .fontColor(Theme.MUTED)
      }
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  healthCard() {
    Column({ space: 14 }) {
      Row() {
        Text('后端健康')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Blank()
        Button(this.loading ? '检查中…' : '刷新')
          .type(ButtonType.Capsule)
          .height(32)
          .fontSize(12)
          .fontColor(Theme.SEAL)
          .backgroundColor('#F7E4DF')
          .enabled(!this.loading)
          .onClick(() => {
            this.loadData();
          })
      }
      .width('100%')

      if (this.health !== null) {
        this.healthContent(this.health)
      } else if (this.loading) {
        Row({ space: 10 }) {
          LoadingProgress()
            .width(24)
            .height(24)
            .color(Theme.SEAL)
          Text('正在请求 /api/health 与 /api/seals …')
            .fontSize(12)
            .fontColor(Theme.MUTED)
        }
        .width('100%')
      } else {
        Text('尚未取得后端健康状态。填入可访问的 API 地址后点击刷新。')
          .fontSize(12)
          .fontColor(Theme.MUTED)
          .width('100%')
      }
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  errorBanner() {
    Row({ space: 10 }) {
      Text('!')
        .fontSize(14)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.WHITE)
        .width(24)
        .height(24)
        .textAlign(TextAlign.Center)
        .backgroundColor(Theme.DANGER)
        .borderRadius(12)
      Column({ space: 3 }) {
        Text('真实请求失败')
          .fontSize(13)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.DANGER)
        Text(this.errorMessage)
          .fontSize(11)
          .fontColor(Theme.INK)
          .maxLines(3)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
    }
    .width('100%')
    .padding(12)
    .backgroundColor('#442319')
    .borderRadius(12)
    .border({ width: 1, color: '#EFC5BB' })
  }

  @Builder
  libraryTitle() {
    Row() {
      Column({ space: 2 }) {
        Text('印谱库')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Text('GET /api/seals · 原图来自真实 original_url')
          .fontSize(10)
          .fontColor(Theme.MUTED)
      }
      .alignItems(HorizontalAlign.Start)
      Blank()
      Text(this.seals.length.toString() + ' 件')
        .fontSize(12)
        .fontColor(Theme.SEAL)
        .padding({ left: 10, right: 10, top: 5, bottom: 5 })
        .backgroundColor('#F7E4DF')
        .borderRadius(12)
    }
    .width('100%')
  }

  @Builder
  emptyLibrary() {
    Column({ space: 8 }) {
      Text('暂无可见印谱')
        .fontSize(16)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.INK)
      Text('后端返回 0 条记录。请先在 Web 工作台上传真实印谱；原生页不会生成模拟数据。')
        .fontSize(12)
        .lineHeight(19)
        .fontColor(Theme.MUTED)
        .textAlign(TextAlign.Center)
    }
    .width('100%')
    .padding(24)
    .backgroundColor(Theme.CARD)
    .borderRadius(16)
    .border({ width: 1, color: Theme.LINE })
  }

  @Builder
  nativeLimitNote() {
    Column({ space: 6 }) {
      Text('原生范围说明')
        .fontSize(11)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.MUTED)
      Text('当前仅原生实现健康检查、印谱列表、详情与设置；没有原生拍摄、修复、AI 推理或 3D 视口。')
        .fontSize(11)
        .lineHeight(18)
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
          this.hero()

          if (this.errorMessage.length > 0) {
            this.errorBanner()
          }

          this.healthCard()
          this.libraryTitle()

          if (this.seals.length > 0) {
            ForEach(this.seals, (item: SealRecord) => {
              SealCard({
                seal: item,
                apiBaseUrl: this.apiBaseUrl,
                onOpen: (id: string) => {
                  this.openDetail(id);
                }
              })
            }, (item: SealRecord) => item.id)
          } else if (!this.loading) {
            this.emptyLibrary()
          }

          this.nativeLimitNote()
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
