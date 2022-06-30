import {HelpPanel, Link, SpaceBetween} from "@awsui/components-react";
import React from "react";

const ToolHelp = ({helpContent}) => {

  if (helpContent) {
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
      {helpContent.content_html ?
        <div dangerouslySetInnerHTML={{__html: helpContent.content_html.replaceAll('\n', '<br>')}}/> : undefined}
      {helpContent.content_text ? helpContent.content_text.replaceAll('\n', '<br>') : undefined}
      {helpContent.content_md ? helpContent.content_md : undefined}
    </HelpPanel>
  } else {
    return null
  }
};

export default ToolHelp;