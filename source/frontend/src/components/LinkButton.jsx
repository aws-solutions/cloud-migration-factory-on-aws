import React from 'react';
import { useHistory } from 'react-router-dom';
import { Button, ButtonProps } from '@awsui/components-react';

type LinkButtonProps = ButtonProps & {
  href: string;
};

const LinkButton = (props: React.PropsWithChildren<LinkButtonProps>): React.ReactElement => {
  const history = useHistory();

  const handleClick = React.useCallback(
    (event: CustomEvent<ButtonProps.ClickDetail>) => {
      // don't intercept the click if the user is trying to open it in a new tab or window
      if (!event.detail.ctrlKey && !event.detail.metaKey) {
        event.preventDefault();
        history.push({
                      pathname: props.href,
                      app: props.app
                    });
      }
    },
    [history, props.href, props.app]
  );

  return (
    <Button {...props} href={props.href} onClick={handleClick}></Button>
  );
};

export default LinkButton;
