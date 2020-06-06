import * as React from "react";

import Designer from "react-designer";

export type SVGJSONType = {
  height: number;
  width: number;
  objects: {
    x: number;
    y: number;
    rotate: number,
    stroke: string,
    strokeWidth: number,
    moveX: number;
    moveY: number;
    path: [];
    closed: boolean;
    fill: string | null;
    type: string;
  }[];
};

const Editor: React.ComponentType<{
  data: SVGJSONType | null;
}> = ({ data }) => {
  const [objects, handleUpdate] = React.useState(data?.objects || []);
  React.useEffect(() => {
    handleUpdate(data?.objects || []);
  }, [data?.objects]);
  console.log(data);
  return (
    <Designer
      width={data?.width}
      height={data?.height}
      background={"#444"}
      objects={objects}
      onUpdate={handleUpdate}
    />
  );
};

export default Editor;
