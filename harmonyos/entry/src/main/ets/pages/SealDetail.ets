import { router } from '@kit.ArkUI';
import { ApiClient } from '../service/ApiClient';
import { ArtifactRecord, DetailRouteParams, SealRecord } from '../model/Models';
import { resolveBackendUrl } from '../common/UrlUtils';
import { formatTimestamp, shortId } from '../common/Format';
import { Theme } from '../common/Theme';

@Entry
@Component
struct SealDetail {
  @State seal: SealRecord | null = null;
  @State loading: boolean = true;
  @State errorMessage: string = '';
  @State imageFailed: boolean = false;
  private sealId: string = '';
  private apiBaseUrl: string = '';

  aboutToAppear(): void {
    try {
      const params: DetailRouteParams = router.getParams() as DetailRouteParams;
      this.sealId = params.id;
      this.apiBaseUrl = params.apiBaseUrl;
      if (this.sealId.length === 0) {
        this.loading = false;
        this.errorMessage = '页面缺少印谱 ID。';
        return;
      }
      this.loadDetail();
    } catch (error) {
      this.loading = false;
      this.errorMessage = '页面参数读取失败，请从印谱库重新进入。';
    }
  }

  private async loadDetail(): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    try {
      const result: SealRecord = await ApiClient.fetchSeal(this.apiBaseUrl, this.sealId);
      this.seal = result;
    } catch (error) {
      this.errorMessage = error instanceof Error ? error.message : '未知错误';
    } finally {
      this.loading = false;
    }
  }

  private imageUrl(): string {
    if (this.seal === null) {
      return '';
    }
    return resolveBackendUrl(this.apiBaseUrl, this.seal.original_url);
  }

  private sourceLabel(kind: string): string {
    if (kind === 'user_upload') {
      return '用户上传';
    }
    if (kind === 'synthetic_test') {
      return '合成测试';
    }
    return kind.length > 0 ? kind : '来源未知';
  }

  private artifactCount(): number {
    return this.seal === null || this.seal.artifacts === undefined ? 0 : this.seal.artifacts.length;
  }

  private sha256Text(seal: SealRecord): string {
    const digest: string = seal.sha256;
    return digest !== undefined && digest.length > 0 ? shortId(digest) : '后端未返回';
  }

  @Builder
  header() {
    Row({ space: 12 }) {
      Button('‹')
        .width(38)
        .height(38)
        .fontSize(24)
        .fontColor(Theme.INK)
        .backgroundColor(Theme.CARD)
        .border({ width: 1, color: Theme.LINE })
        .borderRadius(19)
        .onClick(() => {
          router.back();
        })
      Column({ space: 2 }) {
        Text('印谱详情')
          .fontSize(23)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Text('GET /api/seals/{id}')
          .fontSize(10)
          .fontColor(Theme.MUTED)
      }
      .alignItems(HorizontalAlign.Start)
      Blank()
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 16, bottom: 12 })
  }

  @Builder
  imageBlock() {
    Stack({ alignContent: Alignment.Center }) {
      if (this.imageUrl().length === 0) {
        Column({ space: 6 }) {
          Text('印')
            .fontSize(42)
            .fontWeight(FontWeight.Bold)
            .fontColor(Theme.SEAL)
          Text('后端未返回 original_url')
            .fontSize(11)
            .fontColor(Theme.MUTED)
        }
      } else if (this.imageFailed) {
        Column({ space: 6 }) {
          Text('印')
            .fontSize(42)
            .fontWeight(FontWeight.Bold)
            .fontColor(Theme.SEAL)
          Text('真实原图加载失败')
            .fontSize(11)
            .fontColor(Theme.MUTED)
        }
      } else {
        Image(this.imageUrl())
          .width('100%')
          .height(300)
          .objectFit(ImageFit.Contain)
          .interpolation(ImageInterpolation.High)
          .onError(() => {
            this.imageFailed = true;
          })
      }
    }
    .width('100%')
    .height(300)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .clip(true)
  }

  @Builder
  infoLine(label: string, value: string) {
    Row() {
      Text(label)
        .fontSize(11)
        .fontColor(Theme.MUTED)
        .width(74)
      Text(value.length > 0 ? value : '—')
        .fontSize(12)
        .fontColor(Theme.INK)
        .layoutWeight(1)
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
    }
    .width('100%')
    .alignItems(VerticalAlign.Top)
  }

  @Builder
  infoBlock(seal: SealRecord) {
    Column({ space: 9 }) {
      Text(seal.title.length > 0 ? seal.title : '未命名印谱')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.INK)
        .width('100%')
      Row({ space: 8 }) {
        Text(this.sourceLabel(seal.source_kind))
          .fontSize(10)
          .fontColor(Theme.SEAL_DARK)
          .padding({ left: 8, right: 8, top: 3, bottom: 3 })
          .backgroundColor('#F7E4DF')
          .borderRadius(9)
        Text(this.artifactCount().toString() + ' 个产物')
          .fontSize(10)
          .fontColor(Theme.MUTED)
      }
      .width('100%')
      this.infoLine('文件名', seal.filename)
      this.infoLine('创建时间', formatTimestamp(seal.created_at))
      this.infoLine('来源类型', seal.source_kind)
      this.infoLine('记录 ID', seal.id)
      this.infoLine('SHA-256', this.sha256Text(seal))
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  artifactRow(artifact: ArtifactRecord) {
    Row({ space: 10 }) {
      Text(artifact.kind.length > 0 ? artifact.kind : '未知')
        .fontSize(11)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.SEAL)
        .padding({ left: 8, right: 8, top: 4, bottom: 4 })
        .backgroundColor('#F7E4DF')
        .borderRadius(8)
      Column({ space: 2 }) {
        Text(shortId(artifact.id))
          .fontSize(11)
          .fontColor(Theme.INK)
        Text(artifact.url)
          .fontSize(9)
          .fontColor(Theme.MUTED)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
    }
    .width('100%')
    .padding({ top: 8, bottom: 8 })
  }

  @Builder
  artifactList(items: ArtifactRecord[]) {
    ForEach(items, (item: ArtifactRecord) => {
      this.artifactRow(item)
    }, (item: ArtifactRecord) => item.id)
  }

  @Builder
  artifactBlock(seal: SealRecord) {
    Column({ space: 4 }) {
      Row() {
        Text('产物清单')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
        Blank()
        Text(this.artifactCount().toString())
          .fontSize(12)
          .fontColor(Theme.SEAL)
      }
      .width('100%')

      if (seal.artifacts !== undefined && seal.artifacts.length > 0) {
        this.artifactList(seal.artifacts)
      } else {
        Text('后端未返回产物。')
          .fontSize(11)
          .fontColor(Theme.MUTED)
      }

      Text('STL / 修复图等产物此处只列出真实 URL；原生页不渲染 3D，也不代替 Web 工作台执行处理。')
        .fontSize(10)
        .lineHeight(16)
        .fontColor(Theme.MUTED)
        .width('100%')
        .padding({ top: 8 })
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .alignItems(HorizontalAlign.Start)
  }

  build() {
    Column() {
      this.header()

      if (this.loading) {
        Column({ space: 10 }) {
          LoadingProgress()
            .width(30)
            .height(30)
            .color(Theme.SEAL)
          Text('正在请求印谱详情…')
            .fontSize(12)
            .fontColor(Theme.MUTED)
        }
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
        .width('100%')
      } else if (this.errorMessage.length > 0) {
        Column({ space: 10 }) {
          Text('详情加载失败')
            .fontSize(17)
            .fontWeight(FontWeight.Bold)
            .fontColor(Theme.DANGER)
          Text(this.errorMessage)
            .fontSize(12)
            .fontColor(Theme.MUTED)
            .textAlign(TextAlign.Center)
          Button('重新加载')
            .type(ButtonType.Capsule)
            .height(36)
            .fontSize(12)
            .fontColor(Theme.WHITE)
            .backgroundColor(Theme.SEAL)
            .onClick(() => {
              this.loadDetail();
            })
        }
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
        .padding(24)
        .width('100%')
      } else if (this.seal !== null) {
        Scroll() {
          Column({ space: 14 }) {
            this.imageBlock()
            this.infoBlock(this.seal)
            this.artifactBlock(this.seal)
            Text('此页为真实后端详情视图，不提供模拟成功或离线缓存数据。')
              .fontSize(10)
              .fontColor(Theme.MUTED)
              .width('100%')
              .textAlign(TextAlign.Center)
          }
          .width('100%')
          .padding({ left: 16, right: 16, bottom: 24 })
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      } else {
        Column({ space: 8 }) {
          Text('没有可显示的详情')
            .fontSize(16)
            .fontColor(Theme.INK)
        }
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.PAPER)
  }
}
