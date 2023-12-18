/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {HelpPanel, Link, SpaceBetween} from "@awsui/components-react";
import React from "react";
import {HelpContent} from "../models/HelpContent";


const ToolHelp = ({helpContent}: {
  helpContent?: HelpContent
}) => {

  if (!helpContent) {
    return null
  }

  function getContent({content, content_html, content_md, content_text}: HelpContent) {
    if (content_html) {
      // @ts-ignore
      return <div dangerouslySetInnerHTML={{__html: content_html.replaceAll('\n', '<br>')}}/>
    }

    if (content_text || content) {
      // @ts-ignore
      return <>{(content_text ?? content).replaceAll('\n', '<br>')}</>;
    }

    if (content_md) {
      return <>{content_md}</>;
    }
    return <></>;
  }

  return <HelpPanel
    header={<h2>{helpContent.header}</h2>}
    footer={
      helpContent.content_links
        ?
        <div>
          <h3>
            Learn more
          </h3>
          <SpaceBetween size={'xs'}>
            {helpContent.content_links ? helpContent.content_links.map(item => {
                return (
                  <Link
                    key={'content_link-' + item['key']}
                    external
                    externalIconAriaLabel="Opens in a new tab"
                    href={item['value']}
                  >
                    {item['key']}
                  </Link>
                )
              }
            ) : undefined}
          </SpaceBetween>
        </div>
        :
        undefined
    }
  >
    {getContent(helpContent)}
  </HelpPanel>

};

export default ToolHelp;