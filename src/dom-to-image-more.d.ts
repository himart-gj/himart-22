declare module 'dom-to-image-more' {
  export interface Options {
    filter?: (node: Node) => boolean;
    bgcolor?: string;
    width?: number;
    height?: number;
    style?: Record<string, string | number>;
    quality?: number;
    imagePlaceholder?: string;
    cacheBust?: boolean;
    scale?: number;
  }

  export interface DomToImage {
    toSvg(node: Node, options?: Options): Promise<string>;
    toPng(node: Node, options?: Options): Promise<string>;
    toJpeg(node: Node, options?: Options): Promise<string>;
    toBlob(node: Node, options?: Options): Promise<Blob>;
    toPixelData(node: Node, options?: Options): Promise<Uint8ClampedArray>;
    toCanvas(node: Node, options?: Options): Promise<HTMLCanvasElement>;
  }

  const domToImage: DomToImage;
  export default domToImage;
}
