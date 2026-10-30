import { useEffect, useState } from "react";
import { Avatar, Button } from "antd";
import { ImageUploadFlow } from "./ImageUploadFlow";

const AVATAR_SIZE = 48;

export function AvatarUpload({ reload, avatar, name = "" }: { reload: () => Promise<void>; avatar?: string; name?: string }) {
  const [editing, setEditing] = useState(false);
  const [savedAvatar, setSavedAvatar] = useState(avatar);
  useEffect(() => { setSavedAvatar(avatar); }, [avatar]);
  return <div className="af-avatar-editor">
    {editing ? <ImageUploadFlow kind="avatar" reload={reload} onCancel={() => setEditing(false)}
      onUploaded={(result) => setSavedAvatar(result.avatar)} />
      : <div className="af-avatar-editor-row"><Avatar className="af-avatar" size={AVATAR_SIZE} src={savedAvatar}>{name.slice(0, 1)}</Avatar>
        <div><Button onClick={() => setEditing(true)}>更换头像</Button><p className="af-mall-note">支持 PNG、JPG、GIF、WebP 图片。</p></div>
      </div>}
  </div>;
}
