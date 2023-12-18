export interface Tag {
  /**
   * The key of the tag that will be displayed in the corresponding key field.
   */
  key: string;
  /**
   * The value of the tag that will be displayed in the corresponding value field.
   */
  value: string;
  /**
   * Whether this is an existing tag for the resource. If set to `true`, deletion of the tag will set the `markedForRemoval` property to `true`. If set to `false`, deletion of the tag will remove the tag from the `tags` list.
   */
  existing: boolean;
  /**
   * Whether this tag has been marked for removal. This property will be set to `true` by the component when a user tries to remove an existing tag. The item will remain in the `tags` list. When set to `true`, the user will be presented with the option to undo the removal operation.
   */
  markedForRemoval?: boolean;
}

export type HelpContent = {
  header?: string,
  content_html?: string,
  content_text?: string,
  content?: string, // TODO some parts of the app pass `content` instead of `content_text`, that's probably a bug
  text?: string;
  content_md?: string,
  content_links?: Tag[]
};