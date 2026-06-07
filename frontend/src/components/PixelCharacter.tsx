import type { AvatarState } from "../avatar/types";
import "../avatar/stateAnimations.css";
import "./PixelCharacter.css";

type PixelCharacterProps = {
  state: AvatarState;
};

export function PixelCharacter({ state }: PixelCharacterProps) {
  return (
    <div className="stage" data-state={state}>
      <div className="pixel-person" aria-label={`Boxi is ${state}`}>
        <div className="antenna" />
        <div className="head">
          <div className="eye eye-left" />
          <div className="eye eye-right" />
          <div className="mouth" />
          {state === "worried" ? <div className="worry-mark" aria-hidden="true" /> : null}
        </div>
        <div className="body" />
        <div className="arm arm-left" />
        <div className="arm arm-right" />
      </div>
    </div>
  );
}
