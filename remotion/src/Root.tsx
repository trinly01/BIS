import { Composition } from "remotion";
import { BisPromo } from "./BisPromo";
import { BisAd } from "./BisAd";
import { BisTutorial } from "./BisTutorial";

export const Root: React.FC = () => {
  return (
    <>
      <Composition id="BisPromo" component={BisPromo} durationInFrames={300} fps={30} width={1920} height={1080} />
      <Composition id="BisAd-9x16" component={() => <BisAd vertical />} durationInFrames={300} fps={30} width={1080} height={1920} />
      <Composition id="BisAd-1x1" component={BisAd} durationInFrames={300} fps={30} width={1080} height={1080} />
      <Composition id="BisAd-16x9" component={BisAd} durationInFrames={300} fps={30} width={1920} height={1080} />
      <Composition id="BisTutorial-16x9" component={BisTutorial} durationInFrames={540} fps={30} width={1920} height={1080} />
      <Composition id="BisTutorial-9x16" component={BisTutorial} durationInFrames={540} fps={30} width={1080} height={1920} />
      <Composition id="BisTutorial-1x1" component={BisTutorial} durationInFrames={540} fps={30} width={1080} height={1080} />
    </>
  );
};
