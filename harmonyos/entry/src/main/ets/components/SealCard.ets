import { SealRecord } from '../model/Models';
import { resolveBackendUrl } from '../common/UrlUtils';
import { formatTimestamp } from '../common/Format';
import { Theme } from '../common/Theme';

@Component
export struct SealCard {
  @Prop @Watch('resetImageState') seal: SealRecord = new SealRecord();
  @Prop @Watch('resetImageState') apiBaseUrl: string = '';
  onOpen: (id: string) => void = () => {
  };
  @State imageLoaded: boolean = false;
  @State imageFailed: boolean = false;

  private imageUrl(): string {
    return resolveBackendUrl(this.apiBaseUrl, this.seal.original_url);
  }

  private sourceLabel(): string {
    if (this.seal.source_kind === 'user_upload') {
      return '用户上传';
    }
    if (this.seal.source_kind === 'synthetic_test') {
      return '合成测试';
    }
    return this.seal.source_kind.length > 0 ? this.seal.source_kind : '来源未知';
  }

  private artifactCount(): number {
    return this.seal.artifacts === undefined ? 0 : this.seal.artifacts.length;
  }

  private titleText(): string {
    return this.seal.title.length > 0 ? this.seal.title : '未命名印谱';
  }

  private resetImageState(): void {
    this.imageLoaded = false;
    this.imageFailed = false;
  }

  @Builder
  imagePlaceholder(message: string) {
    Column({ space: 8 }) {
      Text('印')
        .fontSize(40)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.SEAL)
      Text(message)
        .fontSize(12)
        .fontColor(Theme.MUTED)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Column() {
      Stack({ alignContent: Alignment.Center }) {
        if (this.imageUrl().length === 0) {
          this.imagePlaceholder('后端未返回 original_url')
        } else if (this.imageFailed) {
          this.imagePlaceholder('原图加载失败，请检查 API 地址或文件服务')
        } else {
          Image(this.imageUrl())
            .width('100%')
            .height(196)
            .objectFit(ImageFit.Cover)
            .interpolation(ImageInterpolation.High)
            .onComplete(() => {
              this.imageLoaded = true;
            })
            .onError(() => {
              this.imageFailed = true;
              this.imageLoaded = false;
            })
          if (!this.imageLoaded) {
            LoadingProgress()
              .width(30)
              .height(30)
              .color(Theme.SEAL)
          }
        }
      }
      .width('100%')
      .height(196)
      .backgroundColor(Theme.PAPER_DEEP)

      Column({ space: 8 }) {
        Row({ space: 8 }) {
          Text(this.sourceLabel())
            .fontSize(11)
            .fontColor(Theme.SEAL_DARK)
            .padding({ left: 8, right: 8, top: 3, bottom: 3 })
            .backgroundColor('#F7E4DF')
            .borderRadius(10)
          Blank()
          Text(this.artifactCount().toString() + ' 个产物')
            .fontSize(11)
            .fontColor(Theme.MUTED)
        }
        .width('100%')

        Text(this.titleText())
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.INK)
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')
          .textAlign(TextAlign.Start)

        Text(this.seal.filename.length > 0 ? this.seal.filename : '无原始文件名')
          .fontSize(12)
          .fontColor(Theme.MUTED)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')

        Row() {
          Text(formatTimestamp(this.seal.created_at))
            .fontSize(11)
            .fontColor(Theme.MUTED)
          Blank()
          Text('查看原生详情 ›')
            .fontSize(12)
            .fontColor(Theme.SEAL)
        }
        .width('100%')
      }
      .padding(16)
      .width('100%')
      .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .backgroundColor(Theme.CARD)
    .borderRadius(18)
    .border({ width: 1, color: Theme.LINE })
    .clip(true)
    .shadow({ radius: 16, color: '#16000000', offsetX: 0, offsetY: 6 })
    .onClick(() => {
      this.onOpen(this.seal.id);
    })
  }
}
