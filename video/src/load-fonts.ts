import { staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";

let loaded = false;

// Local IBM Plex fonts (OFL). Loaded via JS so bundling does not try to resolve /fonts URLs.
export const loadFonts = (): boolean => {
  if (loaded) return true;
  loaded = true;
  loadFont({
    family: "IBM Plex Sans",
    url: staticFile("fonts/IBMPlexSans-Regular.woff2"),
    weight: "100 700",
  });
  loadFont({
    family: "IBM Plex Sans SemiBold",
    url: staticFile("fonts/IBMPlexSans-SemiBold.woff2"),
    weight: "100 700",
  });
  loadFont({
    family: "IBM Plex Mono",
    url: staticFile("fonts/IBMPlexMono-Regular.woff2"),
    weight: "400",
  });
  return true;
};
